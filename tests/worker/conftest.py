import pytest
import pytest_asyncio

from db.models import Printer
from printer.models import PrinterState, Temperature
from service import JobService
from tests.worker.dummy_printer import DummyPrinter
from worker import PrinterWorker, LatestPrinterStatus


@pytest_asyncio.fixture
async def printer_worker(
    mock_printer: Printer, dummy_printer: DummyPrinter, job_service: JobService
) -> PrinterWorker:
    async with PrinterWorker(
        printer=mock_printer, api=dummy_printer, job_service=job_service
    ) as worker:
        yield worker


@pytest.fixture
def dummy_printer(mock_printer: Printer) -> DummyPrinter:
    return DummyPrinter(url=mock_printer.url)


@pytest.fixture
def printer_state(mock_printer: Printer) -> LatestPrinterStatus:
    return LatestPrinterStatus(
        state=PrinterState.Ready,
        name=mock_printer.opcua_name,
        url=mock_printer.url,
        camera_url=mock_printer.camera_url,
        model=mock_printer.model,
        temp_bed=Temperature(actual=0, target=0),
        temp_nozzle=Temperature(actual=0, target=0),
    )
