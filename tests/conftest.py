import asyncio
from datetime import datetime

import pytest
from _pytest.fixtures import FixtureRequest

from db.core import Database, DatabaseSession
from db.models import User, Order
from octo import MockOctoClient
from opcuax.mock import MockOpcuaClient
from opcuax.objects import OpcuaPrinter
from tests.config import PrinterHost, GcodeFile


@pytest.fixture
def admin_user() -> User:
    return User(id=1, name="foo", permission="admin")


@pytest.fixture
def normal_user() -> User:
    return User(id=2, name="bar", permission="user")


@pytest.fixture
def users(admin_user, normal_user) -> list[User]:
    return [admin_user, normal_user]


@pytest.fixture
def admin_new_order(admin_user) -> Order:
    return Order(id=1, user_id=admin_user.id, gcode_file_path="A.gcode")


@pytest.fixture
def admin_approved_order(admin_user) -> Order:
    return Order(
        id=2,
        user_id=admin_user.id,
        gcode_file_path=GcodeFile.A,
        printer_ip=PrinterHost.Host1,
        approval_time=datetime(2023, 11, 1, 12, 0, 0),
    )


@pytest.fixture
def admin_printing_order(admin_user) -> Order:
    return Order(
        id=3,
        user_id=admin_user.id,
        gcode_file_path=GcodeFile.A,
        printer_ip=PrinterHost.Host1,
        approval_time=datetime(2023, 11, 1, 12, 0, 0),
        print_start_time=datetime(2023, 11, 2, 11, 0, 0),
    )


@pytest.fixture
def admin_printed_order(admin_user) -> Order:
    return Order(
        id=4,
        user_id=admin_user.id,
        gcode_file_path=GcodeFile.A,
        printer_ip=PrinterHost.Host1,
        approval_time=datetime(2023, 11, 1, 12, 0, 0),
        print_start_time=datetime(2023, 11, 2, 11, 0, 0),
        print_end_time=datetime(2023, 11, 5, 9, 0, 0),
    )


@pytest.fixture
def admin_approved_order2(admin_user) -> Order:
    return Order(
        id=5,
        user_id=admin_user.id,
        gcode_file_path=GcodeFile.A,
        printer_ip=PrinterHost.Host1,
        approval_time=datetime(2023, 11, 2, 12, 0, 0),
    )


@pytest.fixture
def admin_orders(
    admin_new_order,
    admin_approved_order,
    admin_printing_order,
    admin_printed_order,
    admin_approved_order2,
) -> list[Order]:
    return [
        admin_new_order,
        admin_approved_order,
        admin_printing_order,
        admin_printed_order,
        admin_approved_order2,
    ]


@pytest.fixture
async def memory_db(request: FixtureRequest) -> Database:
    db = Database(url="sqlite+aiosqlite://")
    await db.create_db_and_tables()

    request.addfinalizer(lambda: asyncio.run(db.close()))

    return db


@pytest.fixture
async def memory_db_with_no_printing_orders(
    memory_db,
    users,
    admin_new_order,
    admin_approved_order,
    admin_printed_order,
) -> Database:
    db = await memory_db

    async with db.open_session() as session:
        session.add_all(
            [*users, admin_new_order, admin_approved_order, admin_printed_order]
        )
        await session.commit()

    return db


@pytest.fixture
async def memory_db_session(
    memory_db, users, admin_orders, request: FixtureRequest
) -> DatabaseSession:
    db = await memory_db

    session = db.open_session()

    async with session as session:
        async with session.begin():
            session.add_all([*users, *admin_orders])

    request.addfinalizer(lambda: asyncio.run(session.close()))

    return session


@pytest.fixture
def mock_opcua_printer1():
    return MockOpcuaClient(delay=0.01).get_object(OpcuaPrinter, namespace_idx=1)


@pytest.fixture
def mock_octo_printer1(request: FixtureRequest) -> MockOctoClient:
    client = MockOctoClient(host=PrinterHost.Host1)
    return client
