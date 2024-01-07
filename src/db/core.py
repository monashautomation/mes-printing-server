from datetime import datetime
from typing import TypeVar, Sequence, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlmodel import select, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Base, Order

DBModel = TypeVar("DBModel", bound=Base)
DBSession = TypeVar("DBSession", bound=AsyncSession)


class DatabaseSession(AsyncSession):
    async def upsert(self, instance: DBModel) -> None:
        self.add(instance)
        await self.commit()
        await self.refresh(instance)

    async def all(self, cls: Type[DBModel]) -> Sequence[DBModel]:
        result = await self.exec(select(cls))
        return result.all()

    async def user_orders(self, user_id: int) -> Sequence[Order]:
        stmt = select(Order).where(Order.user_id == user_id)
        result = await self.exec(stmt)
        return result.all()

    async def current_order(self, printer_id: int) -> Optional[Order]:
        stmt = select(Order).where(
            Order.printer_id == printer_id,
            Order.cancelled_time.is_(None),
            Order.print_start_time.is_not(None),
            Order.print_end_time.is_(None),
        )
        result = await self.exec(stmt)
        return result.one_or_none()

    async def next_order_fifo(self) -> Optional[Order]:
        stmt = select(Order).where(
            Order.cancelled_time.is_(None),
            Order.approval_time.is_not(None),
            Order.print_start_time.is_(None),
        )

        result = await self.exec(stmt)
        return result.first()

    async def approve_order(self, order: Order) -> None:
        if order.approval_time is None:
            order.approval_time = datetime.now()
            await self.upsert(order)

    async def start_printing(self, order: Order) -> None:
        if order.print_start_time is None:
            order.print_start_time = datetime.now()
            await self.upsert(order)

    async def finish_printing(self, order: Order) -> None:
        if order.print_end_time is None:
            order.print_end_time = datetime.now()
            await self.upsert(order)

    async def cancel_order(self, order: Order) -> None:
        if order.cancelled_time is None:
            order.cancelled_time = datetime.now()
            await self.upsert(order)

    async def finish_order(self, order: Order) -> None:
        if order.finish_time is None:
            order.finish_time = datetime.now()
            await self.upsert(order)


class Database:
    def __init__(self, url: str, echo: bool = False):
        self.engine: AsyncEngine = create_async_engine(url, echo=echo)
        self.session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=DatabaseSession
        )

    async def create_db_and_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    def open_session(self) -> DatabaseSession:
        return self.session_maker()

    async def close(self) -> None:
        await self.engine.dispose()
