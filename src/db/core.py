from datetime import datetime
from typing import TypeVar, Sequence, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from db.models import Base, Order

DBModel = TypeVar("DBModel", bound=Base)
DBSession = TypeVar("DBSession", bound=AsyncSession)


def query(operation):
    async def with_session(session: DBSession, *args):
        async with session as session:
            return await operation(session, *args)

    return with_session


def update(operation):
    async def with_session(session: DBSession, *args):
        async with session:
            await operation(session, *args)
            await session.commit()

    return with_session


class DatabaseSession(AsyncSession):
    @update
    async def create(self, instance: DBModel) -> None:
        self.add(instance)

    @query
    async def all(self, cls: Type[DBModel]) -> Sequence[DBModel]:
        result = await self.scalars(select(cls))
        return result.all()

    @query
    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        return await self.get(Order, order_id)

    @query
    async def get_current_order(self, printer_ip: str) -> Optional[Order]:
        statement = select(Order).where(
            Order.printer_ip == printer_ip,
            Order.cancelled_time.is_(None),
            Order.print_start_time.is_not(None),
            Order.print_end_time.is_(None),
        )
        result = await self.scalars(statement)

        return result.one_or_none()

    @query
    async def next_order_fifo(self) -> Optional[Order]:
        statement = (
            select(Order)
            .where(
                Order.cancelled_time.is_(None),
                Order.approval_time.isnot(None),
                Order.print_start_time.is_(None),
            )
            .order_by(Order.create_time)
        )
        result = await self.scalars(statement)

        return result.first()

    @update
    async def approve_order(self, order: Order) -> None:
        if order.approval_time is None:
            order.approval_time = datetime.now()
            self.add(order)

    @update
    async def start_printing(self, order: Order) -> None:
        if order.print_start_time is None:
            order.print_start_time = datetime.now()
            self.add(order)

    @update
    async def finish_printing(self, order: Order) -> None:
        if order.print_end_time is None:
            order.print_end_time = datetime.now()
            self.add(order)

    @update
    async def cancel_order(self, order: Order) -> None:
        if order.cancelled_time is None:
            order.cancelled_time = datetime.now()
            self.add(order)

    @update
    async def finish_order(self, order: Order) -> None:
        if order.finish_time is None:
            order.finish_time = datetime.now()
            self.add(order)


class Database:
    def __init__(self, url: str, echo: bool = False):
        self.engine: AsyncEngine = create_async_engine(url, echo=echo)
        self.worker_session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=DatabaseSession
        )

    async def create_db_and_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def open_session(self) -> DatabaseSession:
        return self.worker_session_maker()

    async def close(self) -> None:
        await self.engine.dispose()
