import pytest

from opcuax.types import BaseOpcuaClient


def test_context_variables_are_set(opcua_printer1):
    printer = opcua_printer1
    assert printer.__client__ is not None
    assert isinstance(printer.__client__, BaseOpcuaClient)
    assert printer.__ns__ == 1


@pytest.mark.asyncio
async def test_get_default_value(opcua_client, printer1_name_node):
    node_id, _ = printer1_name_node
    default_value = "unknown"

    value = await opcua_client.get(node_id, default=default_value)

    assert value == default_value
    assert opcua_client.table[node_id] == default_value


@pytest.mark.asyncio
async def test_get(opcua_client, printer1_name_node):
    node_id, name = printer1_name_node

    opcua_client.table[node_id] = name

    actual = await opcua_client.get(node_id)
    assert actual == name


@pytest.mark.asyncio
async def test_set(opcua_client, printer1_name_node):
    node_id, name = printer1_name_node

    await opcua_client.set(node_id, name)
    assert opcua_client.table[node_id] == name
