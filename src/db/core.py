from collections.abc import Sequence
from typing import TypeVar

from pydantic import AnyUrl
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import select, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Base
from setting import app_settings

DBModel = TypeVar("DBModel", bound=Base)
DBSession = TypeVar("DBSession", bound=AsyncSession)


class DatabaseSession(AsyncSession):
    async def upsert(self, instance: DBModel) -> None:
        self.add(instance)
        await self.commit()
        await self.refresh(instance)

    async def exists(self, cls: type[DBModel], pk: int | str) -> bool:
        result = await self.get(cls, pk)
        return result is not None

    async def all(self, cls: type[DBModel]) -> Sequence[DBModel]:
        result = await self.exec(select(cls))
        return result.all()


class Database:
    def __init__(self, url: AnyUrl | str, echo: bool = False):
        self.url: str = str(url)
        self.engine: AsyncEngine = create_async_engine(self.url, echo=echo)
        self.session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=DatabaseSession
        )

    async def create_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    def new_session(self) -> DatabaseSession:
        return self.session_maker()

    async def close(self) -> None:
        await self.engine.dispose()


database: Database = Database(app_settings.database_url)


def init(url: AnyUrl | str | None = None) -> None:
    url = url or app_settings.database_url
    global database
    database = Database(url)


def session() -> DatabaseSession:
    return database.new_session()
