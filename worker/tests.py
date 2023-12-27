import pytest
from _pytest.monkeypatch import MonkeyPatch

import mes
from db.operation import Database, DatabaseSession
from db.models import User, Order
from octo.mock import MockOctoClient
from opcua.mock import MockOpcuaClient
from opcua.objects import OpcuaPrinter
from worker.events import on_cancel, on_pick
from worker.types import JobWorker, JobState, JobEvent


async def create_user_and_order(session: DatabaseSession) -> None:
    async with session as session:
        order = Order(
            gcode_file_path="a.gcode",
            approved=True,
            user=User(user_name="test_user", permission="admin"),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        print(order.id)


async def get_job_worker() -> JobWorker:
    in_memory_db = Database(url="sqlite+aiosqlite://")
    await in_memory_db.create_db_and_tables()
    session = in_memory_db.open_session()

    await create_user_and_order(session)

    opcua_client = MockOpcuaClient()
    await opcua_client.connect()

    return JobWorker(
        session=session,
        opcua_printer=opcua_client.get_object(OpcuaPrinter, namespace_idx=1),
        octo=MockOctoClient(host="mock-printer.unit-test"),
    )


@pytest.mark.asyncio
async def test_initial_state():
    worker = await get_job_worker()

    assert worker.state == JobState.Connecting


@pytest.mark.asyncio
async def test_connecting_to_connected():
    worker = await get_job_worker()

    await worker.work()

    assert worker.state == JobState.Connected


@pytest.mark.asyncio
async def test_connected_to_ready():
    worker = await get_job_worker()

    await worker.work()  # connecting -> connected
    await worker.work()  # connected -> ready

    assert worker.state == JobState.Ready


@pytest.mark.asyncio
async def test_ready_to_heating(monkeypatch: MonkeyPatch):
    worker = await get_job_worker()

    async def mock_next_order() -> Order:
        async with worker.session as session:
            return await session.get_one(Order, 1)

    monkeypatch.setattr(mes, "next_printing_order", mock_next_order)

    worker.state = JobState.Ready

    await worker.work()

    assert worker.state == JobState.Heater
    assert worker.current_order.order_id == 1


@pytest.mark.asyncio
async def test_heating_to_printing():
    pass
