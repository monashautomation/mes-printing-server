import asyncio

import pytest
from _pytest.fixtures import FixtureRequest

from opcua.mock import MockOpcuaClient
from opcua.types import OpcuaObject, OpcuaVariable


class Printer(OpcuaObject):
    name = OpcuaVariable(name="Printer_Name", default="unknown")


@pytest.fixture
async def opcua_client(request: FixtureRequest) -> MockOpcuaClient:
    client = MockOpcuaClient()
    await client.connect()
    request.addfinalizer(lambda: asyncio.run(client.disconnect()))
    return client


@pytest.fixture
async def opcua_printer1(opcua_client) -> Printer:
    client = await opcua_client
    return client.get_object(Printer, namespace_idx=1)


@pytest.fixture
async def opcua_printer2(opcua_client) -> Printer:
    client = await opcua_client
    return client.get_object(Printer, namespace_idx=2)


@pytest.fixture
async def opcua_printers(opcua_client) -> list[Printer]:
    client = await opcua_client
    return [
        client.get_object(Printer, namespace_idx=1),
        client.get_object(Printer, namespace_idx=2),
    ]
