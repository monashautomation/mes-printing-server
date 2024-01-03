import asyncio

import pytest
from async_timeout import timeout

from opcuax.mock import MockOpcuaClient
from tests.opcuax.mock.conftest import Printer


@pytest.mark.asyncio
async def test_get_default(opcua_printer1, printer1_name_node):
    node_id, _ = printer1_name_node
    value = await opcua_printer1.name.get()
    client_value = await opcua_printer1.client().get(node_id)

    assert value == Printer.name.default
    assert client_value == Printer.name.default


@pytest.mark.asyncio
async def test_get(opcua_printer1, printer1_name_node):
    node_id, name = printer1_name_node
    await opcua_printer1.client().set(node_id, name)

    actual = await opcua_printer1.name.get()
    assert actual == name


@pytest.mark.asyncio
async def test_set(opcua_printer1, printer1_name_node):
    node_id, name = printer1_name_node
    await opcua_printer1.name.set(name)

    actual = await opcua_printer1.client().get(node_id)
    assert actual == name


@pytest.mark.asyncio
async def test_mutation(opcua_printer1, opcua_printer2):
    await opcua_printer1.name.set("foo")
    await opcua_printer2.name.set("bar")

    name1 = await opcua_printer1.name.get()
    name2 = await opcua_printer2.name.get()

    assert name1 == "foo"
    assert name2 == "bar"


@pytest.mark.asyncio
async def test_concurrent_set():
    client = MockOpcuaClient(delay=0.25)
    printer1 = client.get_object(Printer, ns=1)
    printer2 = client.get_object(Printer, ns=2)

    async def update_name(foo: Printer, name: str):
        await foo.name.set(name)  # 0.25s
        return await foo.name.get()  # 0.25s

    async with timeout(0.6), asyncio.TaskGroup() as group:
        task1 = group.create_task(update_name(printer1, "printer1"))
        task2 = group.create_task(update_name(printer2, "printer2"))

    assert task1.result() == "printer1"
    assert task2.result() == "printer2"
