import pytest

from opcuax.types import BaseOpcuaClient


@pytest.mark.asyncio
async def test_context_variables_are_set(opcua_printer1):
    printer = opcua_printer1
    assert printer.__client__ is not None
    assert isinstance(printer.__client__, BaseOpcuaClient)
    assert printer.__ns__ == 1


@pytest.mark.asyncio
async def test_get_default_value(opcua_client):
    namespace = "ns=1;s=Printer_Name"
    default_value = "unknown"

    value = await opcua_client.get(namespace, default=default_value)

    assert value == default_value
    assert opcua_client.table[namespace] == default_value


@pytest.mark.asyncio
async def test_get(opcua_client):
    namespace = "ns=1;s=Printer_Name"
    value = "foobar"

    opcua_client.table[namespace] = value

    assert (await opcua_client.get(namespace)) == value


@pytest.mark.asyncio
async def test_set(opcua_client):
    namespace = "ns=1;s=Printer_Name"
    value = "foobar"

    await opcua_client.set(namespace, value)

    assert opcua_client.table[namespace] == value
