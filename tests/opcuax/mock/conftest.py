from typing import Tuple

import pytest
import pytest_asyncio

from opcuax.mock import MockOpcuaClient
from opcuax.core import OpcuaObject, OpcuaVariable


class Printer(OpcuaObject):
    name = OpcuaVariable(name="Printer_Name", default="unknown")


@pytest.fixture
def printer1_name_node() -> Tuple[str, str]:
    return "ns=1;s=Printer_Name", "foobar"  # node id, value


@pytest_asyncio.fixture
async def opcua_client() -> MockOpcuaClient:
    client = MockOpcuaClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
def opcua_printer1(opcua_client) -> Printer:
    return opcua_client.get_object(Printer, ns=1)


@pytest.fixture
def opcua_printer2(opcua_client) -> Printer:
    return opcua_client.get_object(Printer, ns=2)
