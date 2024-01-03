import pytest_asyncio
from _pytest.fixtures import FixtureRequest

from worker import PrinterWorker


@pytest_asyncio.fixture
async def idle_worker(
    memory_db_with_no_printing_orders,
    mock_octo_printer1,
    mock_opcua_printer1,
    request: FixtureRequest,
) -> PrinterWorker:
    db = memory_db_with_no_printing_orders
    session = db.open_session()

    async def notify_pickup(printer_host: str):
        pass

    worker = PrinterWorker(
        session=session,
        octo=mock_octo_printer1,
        opcua_printer=mock_opcua_printer1,
        order_fetcher=session.next_order_fifo,
        pickup_notifier=notify_pickup,
    )

    yield worker
    await worker.session.close()


@pytest_asyncio.fixture
async def printing_worker(idle_worker):
    worker = idle_worker

    for _ in range(3):
        await worker.work()

    for i in range(worker.octo.heater.required_ticks):
        worker.octo.tick()
        await worker.work()

    yield worker


@pytest_asyncio.fixture
async def printed_worker(printing_worker):
    worker = printing_worker

    for i in range(worker.octo.job.required_ticks):
        worker.octo.tick()
        await worker.work()

    yield worker


@pytest_asyncio.fixture
async def waiting_worker(printed_worker):
    worker = printed_worker

    worker.octo.tick()
    await worker.work()

    yield worker
