import asyncio

import pytest
import pytest_asyncio
from pytest import raises

from printer.errors import FileInUse, NotFound, PrinterIsBusy
from printer.mock.core import MockPrinter
from printer.models import PrinterState, Temperature


@pytest.fixture
def gcode_path() -> str:
    return "A.gcode"


@pytest_asyncio.fixture
async def mock_printer() -> MockPrinter:
    printer = MockPrinter(
        url="http://localhost:5000",
        interval=0.05,
        job_time=10,
        bed_expected=50,
        nozzle_expected=60,
    )

    async with printer:
        yield printer


async def test_connect(mock_printer):
    assert mock_printer.connected


async def test_init_states(mock_printer):
    stat = await mock_printer.current_status()
    assert stat.state == PrinterState.Ready
    assert stat.job is None
    assert stat.temp_bed == Temperature(actual=0, target=mock_printer.bed_expected)
    assert stat.temp_nozzle == Temperature(
        actual=0, target=mock_printer.nozzle_expected
    )


async def test_upload_file(mock_printer, gcode_path):
    await mock_printer.upload_file(gcode_path)
    assert gcode_path in mock_printer.files


async def test_delete_file(mock_printer, gcode_path):
    await mock_printer.upload_file(gcode_path)
    await mock_printer.delete_file(gcode_path)

    assert len(mock_printer.files) == 0


async def test_delete_non_existing_file(mock_printer, gcode_path):
    with raises(NotFound):
        await mock_printer.delete_file(gcode_path)


async def test_print_non_existing_file(mock_printer, gcode_path):
    with raises(NotFound):
        await mock_printer.start_job(gcode_path)


async def test_start_job(mock_printer, gcode_path):
    await mock_printer.upload_file(gcode_path)
    await mock_printer.start_job(gcode_path)

    stat = await mock_printer.current_status()
    assert stat.job is not None
    assert stat.job.file_path == gcode_path
    assert stat.job.progress == 0


async def test_start_multiple_jobs(mock_printer, gcode_path):
    await mock_printer.upload_file(gcode_path)
    await mock_printer.start_job(gcode_path)

    with raises(PrinterIsBusy):
        await mock_printer.start_job(gcode_path)


async def test_overwrite_file_in_use(mock_printer, gcode_path):
    await mock_printer.upload_file(gcode_path)
    await mock_printer.start_job(gcode_path)

    with raises(FileInUse):
        await mock_printer.upload_file(gcode_path)


async def test_heating(mock_printer, gcode_path):
    await mock_printer.upload_file(gcode_path)
    await mock_printer.start_job(gcode_path)

    bed_samples = [mock_printer.bed_actual]
    nozzle_samples = [mock_printer.nozzle_actual]

    for i in range(4):
        await asyncio.sleep(mock_printer.interval)
        stat = await mock_printer.current_status()

        bed_samples.append(stat.temp_bed.actual)
        nozzle_samples.append(stat.temp_nozzle.actual)

        assert bed_samples[-1] > bed_samples[-2]
        assert nozzle_samples[-1] > nozzle_samples[-2]

    await asyncio.sleep(mock_printer.interval * 5)
    stat = await mock_printer.current_status()

    assert stat.temp_bed.actual == mock_printer.bed_expected
    assert stat.temp_nozzle.actual == mock_printer.nozzle_expected


async def test_progress(mock_printer, gcode_path):
    await mock_printer.upload_file(gcode_path)
    await mock_printer.start_job(gcode_path)
    await asyncio.sleep(mock_printer.interval * 7)

    progress_samples = []

    for i in range(5):
        await asyncio.sleep(mock_printer.interval)
        stat = await mock_printer.current_status()
        progress_samples.append(stat.job.progress)

    for i in range(len(progress_samples) - 1):
        assert progress_samples[i] < progress_samples[i + 1]

    await asyncio.sleep(mock_printer.interval * 5)
    stat = await mock_printer.current_status()
    assert stat.job.progress == 100.0


async def test_stop_job(mock_printer, gcode_path):
    mock_printer.job_time = 1000
    await mock_printer.upload_file(gcode_path)
    await mock_printer.start_job(gcode_path)
    await mock_printer.stop_job()


async def test_delete_printing_file(mock_printer, gcode_path):
    mock_printer.job_time = 1000
    await mock_printer.upload_file(gcode_path)
    await mock_printer.start_job(gcode_path)

    with raises(FileInUse):
        await mock_printer.delete_file(gcode_path)
