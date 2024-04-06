from pathlib import Path

import pytest
import pytest_asyncio

from db import Database, DatabaseSession
from db.models import Printer
from printer import PrinterApi
from service import JobService
from setting import AppSettings


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        database_url="sqlite+aiosqlite://",
        opcua_server_url="opc.tcp://mock.opcua.local:4840",
        upload_path=tmp_path.absolute(),
        printer_worker_interval=0.02,
        order_fetcher_interval=0.01,
        mock_printer_interval=0.01,
        mock_printer_job_time=10,
        mock_printer_target_bed_temperature=50,
        mock_printer_target_bed_nozzle=60,
    )


@pytest_asyncio.fixture
async def sqlite_session() -> DatabaseSession:
    sqlite = Database(url="sqlite+aiosqlite://")
    await sqlite.create_tables()

    yield sqlite.new_session()

    await sqlite.close()


@pytest_asyncio.fixture
async def job_service(sqlite_session: DatabaseSession) -> JobService:
    async with JobService(db=sqlite_session) as service:
        yield service


@pytest.fixture
def mock_printer() -> Printer:
    return Printer(
        id=1,
        url="http://mock.printer1:5000",
        api_key="key1",
        api=PrinterApi.Mock,
        has_worker=True,
        opcua_name="Printer1",
        model="Mock Printer",
    )
