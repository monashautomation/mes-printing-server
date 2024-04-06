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
    assert len(dummy_printer.files) == 0
    assert dummy_printer.current_job_file is None


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

    assert JobStatus.Printing in job.flag()
    assert job.gcode_file_path in dummy_printer.files
    assert dummy_printer.current_job_file == job.gcode_file_path


async def test_printing_job_and_printer_is_ready(
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

    dummy_printer.files.add("B.gcode")
    dummy_printer.current_job_file = "B.gcode"

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert JobStatus.Picked in job.flag()
    assert {"B.gcode"} == dummy_printer.files
    assert "B.gcode" == dummy_printer.current_job_file


async def test_printing_job_and_printer_is_printing_another_job(
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
    dummy_printer.files.add("B.gcode")
    dummy_printer.current_job_file = "B.gcode"

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert JobStatus.Picked in job.flag()
    assert {"B.gcode"} == dummy_printer.files
    assert "B.gcode" == dummy_printer.current_job_file


async def test_printed_job(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
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
    )
    await printer_worker.job_service.create_job(job)

    printer_state.state = PrinterState.Printing
    printer_state.job = LatestJob(
        file_path="A.gcode", progress=40, time_used=100, time_left=200
    )

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert JobStatus.Cancelled in job.flag()
    assert len(dummy_printer.files) == 0
    assert dummy_printer.current_job_file is None


async def test_printing_job_is_printed(
    printer_worker: PrinterWorker,
    printer_state: LatestPrinterStatus,
    dummy_printer: DummyPrinter,
    mock_printer: Printer,
):
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
    )
    await printer_worker.job_service.create_job(job)

    printer_state.state = PrinterState.Ready
    printer_state.job = LatestJob(
        file_path="A.gcode", progress=100, time_used=100, time_left=0
    )

    await printer_worker.handle_status(job=job, stat=printer_state)

    assert JobStatus.Printed in job.flag()
    assert len(dummy_printer.files) == 0
    assert dummy_printer.current_job_file is None
