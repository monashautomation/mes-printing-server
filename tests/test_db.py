import pytest
from sqlalchemy import select

from db.models import User, Order


@pytest.mark.asyncio
async def test_create_user(memory_db_session, admin_user):
    session = memory_db_session
    user = User(name="moo", permission="user")

    await session.create(user)

    async with session:
        result = await session.scalars(
            select(User).where(
                User.name == user.name, User.permission == user.permission
            )
        )
        u = result.one()
        assert u.id is not None


@pytest.mark.asyncio
async def test_all_users(memory_db_session, users):
    users = await memory_db_session.all_users()

    assert users == users


@pytest.mark.asyncio
async def test_get_current_order(memory_db_session, admin_printing_order):
    order = await memory_db_session.get_order_by_id(admin_printing_order.id)
    assert order.id == admin_printing_order.id


@pytest.mark.asyncio
async def test_get_current_order(
    memory_db_session, admin_printing_order, printer_hosts
):
    order = await memory_db_session.get_current_order(printer_hosts.host1)
    assert order.id == admin_printing_order.id


@pytest.mark.asyncio
async def test_next_order_by_fifo(
    memory_db_session, admin_printing_order, admin_approved_order
):
    order = await memory_db_session.next_order_fifo()
    assert order.id == admin_approved_order.id


@pytest.mark.asyncio
async def test_approve_order(memory_db_session, admin_new_order):
    await memory_db_session.approve_order(admin_new_order)

    order = await memory_db_session.get(Order, admin_new_order.id)
    assert order.approval_time is not None


@pytest.mark.asyncio
async def test_start_order_printing(memory_db_session, admin_new_order):
    await memory_db_session.start_printing(admin_new_order)

    order = await memory_db_session.get(Order, admin_new_order.id)
    assert order.print_start_time is not None


@pytest.mark.asyncio
async def test_finish_order_printing(memory_db_session, admin_new_order):
    await memory_db_session.finish_printing(admin_new_order)

    order = await memory_db_session.get(Order, admin_new_order.id)
    assert order.print_end_time is not None


@pytest.mark.asyncio
async def test_cancel_order(memory_db_session, admin_new_order):
    await memory_db_session.cancel_order(admin_new_order)

    order = await memory_db_session.get(Order, admin_new_order.id)
    assert order.cancelled_time is not None


@pytest.mark.asyncio
async def test_finish_order(memory_db_session, admin_new_order):
    await memory_db_session.finish_order(admin_new_order)

    order = await memory_db_session.get(Order, admin_new_order.id)
    assert order.finish_time is not None
