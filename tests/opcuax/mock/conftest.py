import pytest
import pytest_asyncio
from _pytest.fixtures import FixtureRequest

from opcuax.mock import MockOpcuaClient
from opcuax.types import OpcuaObject, OpcuaVariable


class Printer(OpcuaObject):
    name = OpcuaVariable(name="Printer_Name", default="unknown")


@pytest_asyncio.fixture
async def opcua_client(request: FixtureRequest) -> MockOpcuaClient:
    client = MockOpcuaClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
def opcua_printer1(opcua_client) -> Printer:
    return opcua_client.get_object(Printer, namespace_idx=1)


@pytest.fixture
def opcua_printer2(opcua_client) -> Printer:
    return opcua_client.get_object(Printer, namespace_idx=2)


@pytest.fixture
def opcua_printers(opcua_client) -> list[Printer]:
    return [
        opcua_client.get_object(Printer, namespace_idx=1),
        opcua_client.get_object(Printer, namespace_idx=2),
    ]
