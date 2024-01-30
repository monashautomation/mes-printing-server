import asyncio

from ctx import AppContext
from db.models import JobStatus, Order
from printer import MockPrinter
from setting import AppSettings
from worker import PrinterWorker
from worker.core import WorkerState


async def test_unsync_to_ready(worker1: PrinterWorker):
    await worker1.step()

    assert worker1.state == WorkerState.Ready


async def test_start_job(worker1: PrinterWorker):
    await worker1.step()
    await worker1.step()

    assert worker1.state == WorkerState.Printing


async def test_print_job(worker1: PrinterWorker, settings: AppSettings):
    for _ in range(settings.mock_printer_job_time + 5):
        await worker1.step()
        await asyncio.sleep(worker1.interval)

    job = await worker1.actual_printer.latest_job()
    assert job is not None
    assert worker1.state == WorkerState.WaitPickup


async def test_pickup(worker1: PrinterWorker, settings: AppSettings):
    for _ in range(settings.mock_printer_job_time + 5):
        await worker1.step()
        await asyncio.sleep(worker1.interval)

    assert worker1.state == WorkerState.WaitPickup

    worker1.pickup_finished()
    await worker1.step()

    assert worker1.state == WorkerState.Unsync


async def test_cancel_when_printing(worker1: PrinterWorker):
    printer = worker1.actual_printer
    assert isinstance(printer, MockPrinter)
    printer.interval = 10

    await worker1.step()
    await worker1.step()

    worker1.cancel_job()
    await worker1.step()

    assert worker1.state == WorkerState.Printed


async def test_cancel_when_waiting_pickup(
    worker1: PrinterWorker, settings: AppSettings
):
    for _ in range(settings.mock_printer_job_time + 5):
        await worker1.step()
        await asyncio.sleep(worker1.interval)

    worker1.cancel_job()
    await worker1.step()

    assert worker1.state == WorkerState.WaitPickup


async def test_should_cancel_when_unsync(
    worker1: PrinterWorker, context: AppContext, admin_approved_order: Order
):
    printer = worker1.actual_printer
    gcode_filename = admin_approved_order.gcode_filename()

    assert isinstance(printer, MockPrinter)
    printer.job_time = 1000

    async with context.database.new_session() as session:
        order = await session.get(Order, admin_approved_order.id)
        order.cancelled = True
        order.job_status = JobStatus.Printing
        await session.commit()

    await printer.upload_file(gcode_filename)
    await printer.start_job(gcode_filename)

    await worker1.step()
    assert worker1.state == WorkerState.Printing

    await worker1.step()
    assert worker1.state == WorkerState.Printed
