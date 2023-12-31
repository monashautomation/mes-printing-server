from worker.core import WorkerEvent, WorkerState, PrinterWorker


@PrinterWorker.event_handler(WorkerEvent.Cancel)
async def on_cancel(worker: PrinterWorker) -> None:
    match worker.state:
        case WorkerState.Heating | WorkerState.Printing:
            await worker.octo.cancel()
            worker.state = WorkerState.Connecting  # wait until printer is ready
        case WorkerState.Printed | WorkerState.WaitingForPickup:
            pass  # still need a pickup since printing is finished
        case state:
            worker.logger.error(
                "Event - Cancel - invalid cancellation when job state = %s", state
            )
            return

    await worker.session.cancel_order(worker.current_order)
    worker.current_order = None


@PrinterWorker.event_handler(WorkerEvent.Pick)
async def on_pick(worker: PrinterWorker) -> None:
    worker.logger.info("Event - Picked")
    worker.state = WorkerState.Ready
