from db.models import JobStatus, Order


async def test_create_order(session, user, order):
    await session.upsert(user)

    order.user_id = user.id
    await session.upsert(order)

    assert order.id is not None
    assert order.create_time is not None
    assert order.user_id == user.id


async def test_create_order_by_relationship(session, user, order):
    await session.upsert(user)
    await session.upsert(order)

    assert order.id is not None
    assert order.create_time is not None
    assert order.user_id == user.id


async def test_create_order_and_user(session, user, order):
    await session.upsert(order)

    assert order.id is not None
    assert order.user_id is not None
    assert order.create_time is not None


async def test_order_user(session, user, order):
    await session.upsert(order)

    order = await session.get(Order, order.id)
    assert order.user.name == user.name


async def test_order_printer(session, order, printer):
    await session.upsert(order)

    order = await session.get(Order, order.id)
    assert order.printer.url == printer.url


async def test_assign_printer(session, user, printer, tmp_path):
    order = Order(user=user, gcode_file_path=str(tmp_path), original_filename="A.gcode")
    await session.upsert(order)
    await session.upsert(printer)

    order.printer = printer
    await session.upsert(order)
    assert order.printer_id == printer.id


async def test_approve(session, order):
    await session.upsert(order)
    await session.approve_order(order)

    order = await session.get(Order, order.id)
    assert order.approved


async def test_start_printing(session, order):
    await session.upsert(order)
    await session.approve_order(order)
    await session.start_printing(order)

    order = await session.get(Order, order.id)
    assert order.job_status == JobStatus.Printing


async def test_finish_printing(session, order):
    await session.upsert(order)
    await session.approve_order(order)
    await session.start_printing(order)
    await session.finish_printing(order)

    order = await session.get(Order, order.id)
    assert order.job_status == JobStatus.Printed


async def test_cancel(session, order):
    await session.upsert(order)
    await session.cancel_order(order)

    order = await session.get(Order, order.id)
    assert order.cancelled


async def test_finish(session, order):
    await session.upsert(order)
    await session.approve_order(order)
    await session.start_printing(order)
    await session.finish_printing(order)
    await session.finish_order(order)

    order = await session.get(Order, order.id)
    assert order.job_status == JobStatus.Finished


async def test_get_current_order(session, order):
    await session.upsert(order)
    await session.approve_order(order)
    await session.start_printing(order)
    o = await session.current_order(order.printer_id)
    assert order.id == o.id
