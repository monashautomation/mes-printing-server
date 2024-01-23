from typing import TypeVar, Sequence, Optional, Type

from pydantic import AnyUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlmodel import select, SQLModel, or_, not_
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Base, Order, JobStatus, Printer

DBModel = TypeVar("DBModel", bound=Base)
DBSession = TypeVar("DBSession", bound=AsyncSession)


class DatabaseSession(AsyncSession):
    async def upsert(self, instance: DBModel) -> None:
        self.add(instance)
        await self.commit()
        await self.refresh(instance)

    async def exists(self, cls: Type[DBModel], pk: int) -> bool:
        result = await self.get(cls, pk)
        return result is not None

    async def all(self, cls: Type[DBModel]) -> Sequence[DBModel]:
        result = await self.exec(select(cls))
        return result.all()

    async def active_printers(self) -> Sequence[Printer]:
        stmt = select(Printer).where(Printer.is_active.is_(True))
        result = await self.exec(stmt)
        return result.all()

    async def user_orders(self, user_id: str) -> Sequence[Order]:
        stmt = select(Order).where(Order.user_id == user_id)
        result = await self.exec(stmt)
        return result.all()

    async def current_order(self, printer_id: int) -> Order | None:
        stmt = select(Order).where(
            Order.printer_id == printer_id,
            or_(
                Order.job_status == JobStatus.Printing,
                Order.job_status == JobStatus.Printed,
            ),
        )
        result = await self.exec(stmt)
        return result.one_or_none()

    async def next_order_fifo(self) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(
                Order.approved,
                not_(Order.cancelled),
                Order.job_status == JobStatus.Pending,
            )
            .order_by(Order.create_time)
        )

        result = await self.exec(stmt)
        return result.first()

    async def approve_order(self, order: Order) -> None:
        order.approved = True
        await self.upsert(order)

    async def start_printing(self, order: Order) -> None:
        order.job_status = JobStatus.Printing
        await self.upsert(order)

    async def finish_printing(self, order: Order) -> None:
        order.job_status = JobStatus.Printed
        await self.upsert(order)

    async def picked(self, order: Order) -> None:
        order.job_status = JobStatus.Storage
        await self.upsert(order)

    async def cancel_order(self, order: Order) -> None:
        order.cancelled = True
        await self.upsert(order)

    async def finish_order(self, order: Order) -> None:
        order.job_status = JobStatus.Finished
        await self.upsert(order)


class Database:
    def __init__(self, url: AnyUrl | str, echo: bool = False):
        self.engine: AsyncEngine = create_async_engine(str(url), echo=echo)
        self.session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=DatabaseSession
        )

    async def create_db_and_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    def new_session(self) -> DatabaseSession:
        return self.session_maker()

    async def close(self) -> None:
        await self.engine.dispose()
