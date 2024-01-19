from pathlib import Path

import pytest
import pytest_asyncio

from db import Database, DatabaseSession
from db.models import User, Order, Printer, PrinterApi


@pytest_asyncio.fixture
async def session() -> DatabaseSession:
    db = Database(url="sqlite+aiosqlite://")
    await db.create_db_and_tables()
    async with db.new_session() as session:
        yield session
    await db.close()


@pytest.fixture
def user() -> User:
    return User(id="auth0|foo", name="foo", permission="admin")


@pytest.fixture
def printer() -> Printer:
    return Printer(
        url="http://localhost:5000", api_key="key", opcua_ns=1, api=PrinterApi.OctoPrint
    )


@pytest.fixture
def order(user: User, tmp_path: Path, printer: Printer) -> Order:
    return Order(user=user, gcode_file_path=str(tmp_path), printer=printer)
