import asyncio

from async_timeout import timeout

from opcuax.mock import MockOpcuaClient, MockOpcuaVariable
from tests.opcuax.mock.conftest import Printer


async def test_get_default(opcua_printer1: Printer):
    value = await opcua_printer1.name.get()

    assert value == Printer.name.default


async def test_get(opcua_printer1: Printer):
    assert isinstance(opcua_printer1.name, MockOpcuaVariable)
    opcua_printer1.name.value = "foo"

    value = await opcua_printer1.name.get()
    assert value == "foo"


async def test_set(opcua_printer1: Printer):
    await opcua_printer1.name.set("foo")

    value = await opcua_printer1.name.get()
    assert value == "foo"


async def test_set_null(opcua_printer1: Printer):
    await opcua_printer1.name.set("foo")
    await opcua_printer1.name.set(None)

    value = await opcua_printer1.name.get()
    assert value == Printer.name.default


async def test_nested_get(opcua_printer1: Printer):
    value = await opcua_printer1.job.progress.get()
    assert value == 0


async def test_nested_set(opcua_printer1: Printer):
    await opcua_printer1.job.finished.set(True)

    value = await opcua_printer1.job.finished.get()
    assert value


async def test_to_dict(opcua_printer1: Printer):
    data = await opcua_printer1.to_dict()

    assert data == {
        "name": Printer.name.default,
        "number": Printer.number.default,
        "job": {
            "finished": Printer.job.finished.default,
            "progress": Printer.job.progress.default,
        },
    }


async def test_flattened_to_dict(opcua_printer1: Printer):
    data = await opcua_printer1.to_dict(flatten=True)

    assert data == {
        "name": Printer.name.default,
        "number": Printer.number.default,
        "job_finished": Printer.job.finished.default,
        "job_progress": Printer.job.progress.default,
    }


async def test_isolation(opcua_printer1: Printer, opcua_printer2: Printer):
    await opcua_printer1.name.set("foo")
    await opcua_printer2.name.set("bar")

    name1 = await opcua_printer1.name.get()
    name2 = await opcua_printer2.name.get()

    assert name1 == "foo"
    assert name2 == "bar"


async def test_concurrent_set():
    client = MockOpcuaClient(delay=0.25)
    printer1 = await client.get_object(Printer, name="Printer1")
    printer2 = await client.get_object(Printer, name="Printer2")

    async def update_name(foo: Printer, name: str):
        await foo.name.set(name)  # 0.25s
        return await foo.name.get()  # 0.25s

    async with timeout(0.6), asyncio.TaskGroup() as group:
        task1 = group.create_task(update_name(printer1, "printer1"))
        task2 = group.create_task(update_name(printer2, "printer2"))

    assert task1.result() == "printer1"
    assert task2.result() == "printer2"
