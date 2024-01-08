from db.models import User


async def test_create_user(session, user):
    await session.upsert(user)

    assert user.id is not None
    assert user.create_time is not None


async def test_get_user(session, user):
    await session.upsert(user)
    u = await session.get(User, 1)

    assert u is not None
    assert u.name == user.name


async def test_user_orders(session, user, order):
    await session.upsert(order)
    orders = await session.user_orders(user.id)

    assert orders[0].id == order.id
