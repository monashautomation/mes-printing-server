from datetime import datetime, timedelta

from db.models import Printer, Job, JobStatus
from printer.models import PrinterState, LatestJob
from tests.worker.dummy_printer import DummyPrinter
from worker import PrinterWorker, LatestPrinterStatus


async def test_no_job_and_printer_is_ready(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
):
    await printer_worker.handle_status(job=None, stat=printer_state)
    assert dummy_printer.has_no_uploaded_files()
    assert dummy_printer.is_not_printing()


async def test_no_job_and_printer_is_printing(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
):
    printer_state.job = LatestJob(
        file_path="XYZ.gcode", progress=50, time_used=100, time_left=100
    )
    printer_state.state = PrinterState.Printing

    await printer_worker.handle_status(job=None, stat=printer_state)

    job = await printer_worker.job_service.get_job(printer_filename="XYZ.gcode")
    assert job is not None


async def test_pending_job_and_printer_is_ready(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
    job = Job(
        printer_id=mock_printer.id,
        gcode_file_path="A.gcode",
        status=JobStatus.ToPrint.value,
        from_server=True,
    )
    await printer_worker.job_service.create_job(job)

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert job.is_printing()
    assert dummy_printer.has_file(job.gcode_file_path)
    assert dummy_printer.is_printing_file(job.gcode_file_path)


async def test_prev_job_is_printing_but_printer_is_ready(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
    job = Job(
        printer_id=mock_printer.id,
        gcode_file_path="A.gcode",
        status=(
            JobStatus.Printing
            | JobStatus.Scheduled
            | JobStatus.Approved
            | JobStatus.Created
        ).value,
        from_server=True,
    )
    await printer_worker.job_service.create_job(job)

    await dummy_printer.upload_file("B.gcode")
    await dummy_printer.start_job("B.gcode")

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert job.is_picked()
    assert dummy_printer.is_printing_file("B.gcode")


async def test_prev_job_is_printing_but_printer_is_printing_another_job(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
    job = Job(
        printer_id=mock_printer.id,
        gcode_file_path="A.gcode",
        status=(
            JobStatus.Printing
            | JobStatus.Scheduled
            | JobStatus.Approved
            | JobStatus.Created
        ).value,
        from_server=True,
    )
    await printer_worker.job_service.create_job(job)

    printer_state.state = PrinterState.Printing
    printer_state.job = LatestJob(
        file_path="B.gcode", progress=30, time_used=100, time_left=200
    )
    await dummy_printer.upload_file("B.gcode")
    await dummy_printer.start_job("B.gcode")

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert job.is_picked()
    assert dummy_printer.is_printing_file("B.gcode")


async def test_prev_job_is_is_printed(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
    start_time = datetime.now() - timedelta(seconds=100)
    job = Job(
        printer_id=mock_printer.id,
        gcode_file_path="A.gcode",
        printer_filename="A.gcode",
        status=(
            JobStatus.Printing
            | JobStatus.Scheduled
            | JobStatus.Approved
            | JobStatus.Created
            | JobStatus.Printed
        ).value,
        from_server=True,
        start_time=start_time,
    )
    await printer_worker.job_service.create_job(job)

    printer_state.state = PrinterState.Ready
    printer_state.job = LatestJob(
        file_path="A.gcode", progress=100, time_used=100, time_left=0
    )

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert JobStatus.PickupIssued in job.flag()
    assert len(dummy_printer.files) == 0
    assert dummy_printer.current_job_file is None


async def test_cancel_job(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
    start_time = datetime.now() - timedelta(seconds=100)
    job = Job(
        printer_id=mock_printer.id,
        gcode_file_path="A.gcode",
        printer_filename="A.gcode",
        status=(
            JobStatus.Printing
            | JobStatus.Scheduled
            | JobStatus.Approved
            | JobStatus.Created
            | JobStatus.CancelIssued
        ).value,
        from_server=True,
        start_time=start_time,
    )
    await printer_worker.job_service.create_job(job)

    printer_state.state = PrinterState.Printing
    printer_state.job = LatestJob(
        file_path="A.gcode", progress=40, time_used=100, time_left=200
    )

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert JobStatus.Cancelled in job.flag()
    assert dummy_printer.has_no_uploaded_files()
    assert dummy_printer.is_not_printing()


async def test_printing_job_is_printed(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
    start_time = datetime.now() - timedelta(seconds=100)
    job = Job(
        printer_id=mock_printer.id,
        gcode_file_path="A.gcode",
        printer_filename="A.gcode",
        status=(
            JobStatus.Printing
            | JobStatus.Scheduled
            | JobStatus.Approved
            | JobStatus.Created
        ).value,
        from_server=True,
        start_time=start_time,
    )
    await printer_worker.job_service.create_job(job)

    printer_state.state = PrinterState.Ready
    printer_state.job = LatestJob(
        file_path="A.gcode", progress=100, time_used=100, time_left=0
    )

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert job.is_printed()
    assert dummy_printer.has_no_uploaded_files()
    assert dummy_printer.is_not_printing()


async def test_different_job_with_same_file(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
    start_time = datetime.now() - timedelta(seconds=500)
    job = Job(
        printer_id=mock_printer.id,
        gcode_file_path="A.gcode",
        printer_filename="A.gcode",
        status=(
            JobStatus.Printing
            | JobStatus.Scheduled
            | JobStatus.Approved
            | JobStatus.Created
        ).value,
        from_server=True,
        start_time=start_time,
    )
    await printer_worker.job_service.create_job(job)

    await dummy_printer.upload_file("A.gcode")
    await dummy_printer.start_job("A.gcode")
    printer_state.state = PrinterState.Printing
    printer_state.job = LatestJob(
        file_path="A.gcode", progress=0, time_used=1, time_left=500
    )

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert job.is_picked()
    assert dummy_printer.is_printing_file("A.gcode")
