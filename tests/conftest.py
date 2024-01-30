from pathlib import Path
from typing import List

import pytest
import pytest_asyncio

from ctx import AppContext
from db.models import Order, Printer, User
from printer import PrinterApi
from setting import AppSettings


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        database_url="sqlite+aiosqlite://",
        opcua_server_url="opc.tcp://mock.opcua.local:4840",
        upload_path=tmp_path.absolute(),
        printer_worker_interval=0.01,
        mock_printer_interval=0.01,
        mock_printer_job_time=10,
    )


@pytest_asyncio.fixture
async def context(settings: AppSettings) -> AppContext:
    async with AppContext(settings) as ctx:
        yield ctx


@pytest.fixture
def printer1() -> Printer:
    return Printer(
        id=1,
        api=PrinterApi.Mock,
        url="http://pi1.lab:5000",
        octo_api_key="p1",
        opcua_ns=1,
    )


@pytest.fixture
def printers(printer1) -> list[Printer]:
    return [
        printer1,
        Printer(
            id=2,
            api=PrinterApi.Mock,
            url="http://pi2.lab:5000",
            octo_api_key="p2",
            opcua_ns=2,
        ),
        Printer(
            id=3,
            api=PrinterApi.Mock,
            url="http://pi3.lab:5000",
            octo_api_key="p3",
            opcua_ns=3,
        ),
    ]


@pytest.fixture
def admin() -> User:
    return User(id="auth0|foo", name="foo", permission="admin")


@pytest.fixture
def customer() -> User:
    return User(id="google|bar", name="bar", permission="user")


@pytest.fixture
def users(admin: User, customer: User) -> list[User]:
    return [admin, customer]


@pytest.fixture
def admin_new_order(admin) -> Order:
    return Order(
        id=1, user_id=admin.id, gcode_file_path="A.gcode", original_filename="A.gcode"
    )


@pytest.fixture
def admin_approved_order(admin, printer1, settings) -> Order:
    path = settings.upload_path / "A.gcode"
    path.touch()
    return Order(
        id=2,
        user_id=admin.id,
        gcode_file_path=str(path.absolute()),
        printer_id=printer1.id,
        approved=True,
        original_filename="A.gcode",
    )
