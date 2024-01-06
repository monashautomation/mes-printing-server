from tests.octo.mock.conftest import (
    assert_printer_is_cancelling,
    assert_printer_is_ready,
)


async def test_cancel_during_heating(printer1_after_upload):
    printer = printer1_after_upload

    for _ in range(printer.heater.required_ticks - 1):
        printer.tick()

    await printer.cancel()

    printer_status = await printer.current_printer_status()
    assert_printer_is_cancelling(printer_status)

    printer.tick()

    printer_status = await printer.current_printer_status()
    assert_printer_is_ready(printer_status)

    job_status = await printer.current_job()
    assert job_status.progress.completion == 0


async def test_cancel_during_printing(printer1_after_heating):
    printer = printer1_after_heating

    for _ in range(printer.job.required_ticks - 1):
        printer.tick()

    await printer.cancel()

    printer_status = await printer.current_printer_status()
    assert_printer_is_cancelling(printer_status)

    for _ in range(10):
        printer.tick()

        printer_status = await printer.current_printer_status()
        assert_printer_is_ready(printer_status)

        job_status = await printer.current_job()
        assert job_status.progress.completion < 100
