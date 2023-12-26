import pytest

from tests.octo.mock.conftest import assert_printer_is_printing, assert_printer_is_ready


@pytest.mark.asyncio
async def test_temperature_during_heating(printer1_after_upload):
    printer = await printer1_after_upload

    for i in range(printer.heater.required_ticks):
        printer.tick()

        temp = await printer.current_temperature()

        assert temp.bed.actual == (i + 1) * 20
        assert temp.tool0.actual == (i + 1) * 15


@pytest.mark.asyncio
async def test_temperature_during_printing(printer1_after_heating):
    printer = await printer1_after_heating

    for i in range(printer.job.required_ticks):
        printer.tick()

        temp = await printer.current_temperature()

        assert temp.bed.actual >= 200
        assert temp.tool0.actual >= 150


@pytest.mark.asyncio
async def test_temperature_after_printing(printer1_after_printing):
    printer = await printer1_after_printing

    for i in range(10):
        printer.tick()

        temp = await printer.current_temperature()

        assert temp.bed.actual == 200 - (i + 1) * 20
        assert temp.tool0.actual >= 150 - (i + 1) * 15


@pytest.mark.asyncio
async def test_progress_after_heating(printer1_after_heating):
    printer = await printer1_after_heating

    job_status = await printer.current_job()
    assert job_status.progress.completion == 0


@pytest.mark.asyncio
async def test_progress_during_printing(printer1_after_heating):
    printer = await printer1_after_heating

    for i in range(printer.job.required_ticks):
        printer.tick()

        job_status = await printer.current_job()
        assert job_status.progress.completion == (i + 1) * 10


@pytest.mark.asyncio
async def test_progress_after_printing(printer1_after_printing):
    printer = await printer1_after_printing

    for _ in range(10):
        printer.tick()

        job_status = await printer.current_job()
        assert job_status.progress.completion == 100


@pytest.mark.asyncio
async def test_printer_status_during_heating_and_printing(printer1_after_upload):
    printer = await printer1_after_upload

    for _ in range(printer.heater.required_ticks + printer.job.required_ticks - 1):
        printer.tick()

        printer_status = await printer.current_printer_status()
        assert_printer_is_printing(printer_status)


@pytest.mark.asyncio
async def test_printer_status_after_printing(printer1_after_printing):
    printer = await printer1_after_printing

    for _ in range(10):
        printer_status = await printer.current_printer_status()
        assert_printer_is_ready(printer_status)

        printer.tick()
