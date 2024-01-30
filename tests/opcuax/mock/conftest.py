import pytest
import pytest_asyncio

from opcuax import (
    MockOpcuaClient,
    OpcuaBoolVar,
    OpcuaFloatVar,
    OpcuaIntVar,
    OpcuaObject,
    OpcuaStrVar,
)


class PrinterJob(OpcuaObject):
    finished = OpcuaBoolVar(name="Finished")
    progress = OpcuaFloatVar(name="Progress")


class Printer(OpcuaObject):
    name = OpcuaStrVar(name="Name", default="unknown")
    number = OpcuaIntVar(name="Number")
    job = PrinterJob(name="Job")


@pytest.fixture
def printer1_name_node() -> tuple[str, str]:
    return "ns=1;s=Name", "foobar"  # node id, value


@pytest_asyncio.fixture
async def opcua_client() -> MockOpcuaClient:
    async with MockOpcuaClient() as client:
        yield client


@pytest_asyncio.fixture
async def opcua_printer1(opcua_client) -> Printer:
    return await opcua_client.get_object(Printer, name="printer1")


@pytest_asyncio.fixture
async def opcua_printer2(opcua_client) -> Printer:
    return await opcua_client.get_object(Printer, name="printer2")
