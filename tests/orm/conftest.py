from pathlib import Path

import pytest
import pytest_asyncio

from db import Database, DatabaseSession
from db.models import User, Order, Printer


@pytest_asyncio.fixture
async def session() -> DatabaseSession:
    db = Database(url="sqlite+aiosqlite://")
    await db.create_db_and_tables()
    session = db.open_session()
    yield session
    await session.close()
    await db.close()


@pytest.fixture
def user() -> User:
    return User(name="foo", permission="admin")


@pytest.fixture
def printer() -> Printer:
    return Printer(octo_url="http://localhost:5000", octo_api_key="key", opcua_ns=1)


@pytest.fixture
def order(user: User, tmp_path: Path, printer: Printer) -> Order:
    return Order(user=user, gcode_file_path=str(tmp_path), printer=printer)
