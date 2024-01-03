from collections import namedtuple
from datetime import datetime

import pytest
import pytest_asyncio
from _pytest.fixtures import FixtureRequest

from db.core import Database, DatabaseSession
from db.models import User, Order
from octo import MockOctoClient
from opcuax.mock import MockOpcuaClient
from opcuax.objects import OpcuaPrinter

PrinterHosts = namedtuple("PrinterHost", ["host1", "host2", "host3"])
GcodeFiles = namedtuple("GcodeFiles", ["A", "B", "C"])
Users = namedtuple("Users", ["admin", "user"])


class TestContext:
    pass


@pytest.fixture
def printer_hosts() -> PrinterHosts:
    return PrinterHosts(
        "192.168.228.1:5000", "192.168.228.2:5000", "192.168.228.3:5000"
    )


@pytest.fixture
def gcode_files() -> GcodeFiles:
    return GcodeFiles("A.gcode", "B.gcode", "C.gcode")


@pytest.fixture
def users() -> Users:
    return Users(
        User(id=1, name="foo", permission="admin"),
        User(id=2, name="bar", permission="user"),
    )


@pytest.fixture
def admin_user(users) -> User:
    return users.admin


@pytest.fixture
def normal_user(users) -> User:
    return users.user


@pytest.fixture
def admin_new_order(admin_user) -> Order:
    return Order(id=1, user_id=admin_user.id, gcode_file_path="A.gcode")


@pytest.fixture
def admin_approved_order(admin_user, gcode_files, printer_hosts) -> Order:
    return Order(
        id=2,
        user_id=admin_user.id,
        gcode_file_path=gcode_files.A,
        printer_ip=printer_hosts.host1,
        approval_time=datetime(2023, 11, 1, 12, 0, 0),
    )


@pytest.fixture
def admin_printing_order(admin_user, gcode_files, printer_hosts) -> Order:
    return Order(
        id=3,
        user_id=admin_user.id,
        gcode_file_path=gcode_files.A,
        printer_ip=printer_hosts.host1,
        approval_time=datetime(2023, 11, 1, 12, 0, 0),
        print_start_time=datetime(2023, 11, 2, 11, 0, 0),
    )


@pytest.fixture
def admin_printed_order(admin_user, gcode_files, printer_hosts) -> Order:
    return Order(
        id=4,
        user_id=admin_user.id,
        gcode_file_path=gcode_files.A,
        printer_ip=printer_hosts.host1,
        approval_time=datetime(2023, 11, 1, 12, 0, 0),
        print_start_time=datetime(2023, 11, 2, 11, 0, 0),
        print_end_time=datetime(2023, 11, 5, 9, 0, 0),
    )


@pytest.fixture
def admin_approved_order2(admin_user, gcode_files, printer_hosts) -> Order:
    return Order(
        id=5,
        user_id=admin_user.id,
        gcode_file_path=gcode_files.A,
        printer_ip=printer_hosts.host1,
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


@pytest_asyncio.fixture
async def memory_db(request: FixtureRequest) -> Database:
    db = Database(url="sqlite+aiosqlite://")
    await db.create_db_and_tables()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def memory_db_with_no_printing_orders(
    memory_db,
    users,
    admin_new_order,
    admin_approved_order,
    admin_printed_order,
) -> Database:
    async with memory_db.open_session() as session:
        session.add_all(
            [*users, admin_new_order, admin_approved_order, admin_printed_order]
        )
        await session.commit()
        await session.close()

    yield memory_db


@pytest_asyncio.fixture
async def memory_db_session(
    memory_db, users, admin_orders, request: FixtureRequest
) -> DatabaseSession:
    session = memory_db.open_session()

    async with session, session.begin():
        session.add_all([*users, *admin_orders])

    yield session
    await session.close()


@pytest.fixture
def mock_opcua_printer1():
    return MockOpcuaClient(delay=0.01).get_object(OpcuaPrinter, ns=1)


@pytest.fixture
def mock_octo_printer1(request: FixtureRequest, printer_hosts) -> MockOctoClient:
    client = MockOctoClient(url=printer_hosts.host1)
    return client
