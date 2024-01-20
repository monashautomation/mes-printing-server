import pytest_asyncio

from ctx import AppContext
from db.models import Printer, User
from worker import PrinterWorker


@pytest_asyncio.fixture
async def context(
    context: AppContext, printer1: Printer, admin: User, admin_approved_order
):
    async with context.database.new_session() as session:
        session.add_all([admin, printer1, admin_approved_order])
        await session.commit()
    context.printer_worker(printer1)
    yield context


@pytest_asyncio.fixture
async def worker1(context: AppContext, printer1: Printer) -> PrinterWorker:
    worker = context.workers[printer1.id]
    async with worker:
        yield worker
