import asyncio
from datetime import datetime

import pytest

from opcuax.mock import MockOpcuaClient
from tests.opcuax.mock.conftest import Printer


@pytest.mark.asyncio
async def test_get_default(opcua_printer1):
    obj = await opcua_printer1

    value = await obj.name.get()
    client_value = await obj.__client__.get("ns=1;s=Printer_Name")

    assert value == "unknown"
    assert client_value == "unknown"


@pytest.mark.asyncio
async def test_get(opcua_printer1):
    obj = await opcua_printer1

    value = "foobar"
    await obj.__client__.set("ns=1;s=Printer_Name", value)

    actual = await obj.name.get()

    assert actual == value


@pytest.mark.asyncio
async def test_set(opcua_printer1):
    obj = await opcua_printer1

    value = "foobar"
    await obj.name.set(value)

    actual = await obj.__client__.get("ns=1;s=Printer_Name")

    assert actual == value


@pytest.mark.asyncio
async def test_mutation(opcua_printers):
    printers = await opcua_printers
    [printer1, printer2] = printers

    await printer1.name.set("foo")
    await printer2.name.set("bar")

    name1 = await printer1.name.get()
    name2 = await printer2.name.get()

    assert name1 == "foo"
    assert name2 == "bar"


@pytest.mark.asyncio
async def test_concurrent_set():
    client = MockOpcuaClient(delay=0.25)
    printer1 = client.get_object(Printer, namespace_idx=1)
    printer2 = client.get_object(Printer, namespace_idx=2)

    start_time = datetime.now()

    async def update_name(foo: Printer, name: str):
        await foo.name.set(name)  # 0.25s
        return await foo.name.get()  # 0.25s

    async with asyncio.TaskGroup() as group:
        task1 = group.create_task(update_name(printer1, "printer1"))
        task2 = group.create_task(update_name(printer2, "printer2"))

    sec_used = (datetime.now() - start_time).total_seconds()

    assert task1.result() == "printer1"
    assert task2.result() == "printer2"
    assert sec_used < 0.6
