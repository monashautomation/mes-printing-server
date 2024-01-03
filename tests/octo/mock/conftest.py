import asyncio

import pytest
from _pytest.fixtures import FixtureRequest

from octo import MockOctoClient
from octo.models import OctoPrinterStatus, CurrentPrinterStatus


@pytest.fixture
async def printer1(request: FixtureRequest, printer_hosts) -> MockOctoClient:
    client = MockOctoClient(url=printer_hosts.host1)
    await client.connect()
    request.addfinalizer(lambda: asyncio.run(client.disconnect()))
    return client


@pytest.fixture
async def printer1_after_upload(printer1, gcode_files) -> MockOctoClient:
    printer = await printer1
    await printer.upload_file_to_print(gcode_files.A)
    return printer


@pytest.fixture
async def printer1_after_heating(printer1_after_upload) -> MockOctoClient:
    printer = await printer1_after_upload

    for _ in range(printer.heater.required_ticks):
        printer.tick()

    return printer


@pytest.fixture
async def printer1_after_printing(printer1_after_heating) -> MockOctoClient:
    printer = await printer1_after_heating

    for _ in range(printer.job.required_ticks):
        printer.tick()

    return printer


def assert_printer_is_ready(printer_status: CurrentPrinterStatus):
    assert printer_status.state.text == OctoPrinterStatus.Ready
    assert printer_status.state.flags.ready
    assert not printer_status.state.flags.cancelling
    assert not printer_status.state.flags.printing


def assert_printer_is_printing(printer_status: CurrentPrinterStatus):
    assert printer_status.state.text == OctoPrinterStatus.Printing
    assert printer_status.state.flags.printing
    assert not printer_status.state.flags.ready
    assert not printer_status.state.flags.cancelling


def assert_printer_is_cancelling(printer_status: CurrentPrinterStatus):
    assert printer_status.state.text == OctoPrinterStatus.Cancelling
    assert printer_status.state.flags.cancelling
    assert not printer_status.state.flags.ready
    assert not printer_status.state.flags.printing
