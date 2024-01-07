from db.models import Order
from octo.models import CurrentJob
from worker.core import WorkerState, PrinterWorker, WorkerEvent
from worker.helper import parse_printer_state, is_heating_complete


@PrinterWorker.state_handler(WorkerState.Connecting)
async def when_connecting(worker: PrinterWorker) -> None:
    await worker.octo.connect()
    worker.state = WorkerState.Connected


@PrinterWorker.state_handler(WorkerState.Connected)
async def when_connected(worker: PrinterWorker) -> None:
    printer_status = await worker.octo.current_printer_status()

    worker.state = parse_printer_state(printer_status.state.flags)
    worker.current_order = await worker.session.current_order(worker.printer_id)
    job_status = await worker.octo.current_job()

    match worker.state, worker.current_order:
        case WorkerState.Ready, None:
            worker.logger.info("printer is ready for orders")
            # TODO
            worker.logger.warning(
                "cannot detect if multiple jobs were handled between 2 worker connections"
            )
        case WorkerState.Printing, Order(id=order_id):
            worker.logger.debug("printer is printing order %d", order_id)
        case WorkerState.Ready, Order(id=order_id):
            if job_status.progress.completion == 100:
                worker.state = WorkerState.Printed
            else:
                worker.put_event(WorkerEvent.Cancel)
        case WorkerState.Printing, None:
            worker.logger.error(
                "printer is printing an unknown order, wait until its finished"
            )


@PrinterWorker.state_handler(WorkerState.Ready)
async def when_ready(worker: PrinterWorker) -> None:
    order: Order = await worker.order_fetcher()  # get from the queue system

    if order is None:
        worker.logger.info("no pending orders")
        return

    await worker.octo.upload_file_to_print(order.gcode_file_path)
    await worker.session.start_printing(order)

    worker.current_order = order
    worker.state = WorkerState.Heating


@PrinterWorker.state_handler(WorkerState.Heating)
async def when_heating(worker: PrinterWorker) -> None:
    temp_data = await worker.octo.current_temperature()
    bed = temp_data.bed
    nozzle = temp_data.tool0

    await worker.opcua_printer_updator.update_temperature(bed=bed, nozzle=nozzle)

    worker.logger.info("current temperature: bed=%r, nozzle=%r", bed, nozzle)

    if is_heating_complete(bed) and is_heating_complete(nozzle):
        worker.state = WorkerState.Printing


@PrinterWorker.state_handler(WorkerState.Printing)
async def when_printing(worker: PrinterWorker) -> None:
    job_status: CurrentJob = await worker.octo.current_job()

    await worker.opcua_printer_updator.update_job_progress(job_status)

    worker.logger.info("printing progress: %f", job_status.progress.completion)

    if job_status.progress.completion == 100:
        worker.state = WorkerState.Printed


@PrinterWorker.state_handler(WorkerState.Printed)
async def when_printed(worker: PrinterWorker) -> None:
    await worker.octo.head_jog(x=0, y=0, z=30)
    await worker.session.finish_printing(worker.current_order)

    # Retrieve the file path from the current job's file attribute
    job_status = await worker.octo.current_job()
    file_path = job_status.job.file.path
    await worker.octo.delete_printed_file(file_path)

    await worker.opcua_printer_updator.reset_current_job()

    await worker.pickup_notifier(worker.octo.url)  # notify the matrix system to pickup

    worker.current_order = None
    worker.state = WorkerState.WaitingForPickup


@PrinterWorker.state_handler(WorkerState.WaitingForPickup)
async def when_waiting_for_pickup(worker: PrinterWorker) -> None:
    worker.logger.info("waiting for robot to pickup the printed model")


@PrinterWorker.state_handler(WorkerState.Picked)
async def when_picked(worker: PrinterWorker) -> None:
    worker.state = WorkerState.Ready


@PrinterWorker.state_handler(WorkerState.Error)
async def when_error(worker) -> None:
    worker.logger.error("Printer is in error state")
    worker.state = WorkerState.Connected
