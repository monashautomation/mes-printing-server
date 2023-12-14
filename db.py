from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from models import *


class DatabaseSession:
    def __init__(self, engine: AsyncEngine):
        self.session: AsyncSession = AsyncSession(engine, expire_on_commit=False)

    async def __aenter__(self):
        await self.session.__aenter__()  # starts a transaction
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)


class Database:
    def __init__(
        self,
        url: str,
        echo: bool = False,
    ):
        self.engine: AsyncEngine = create_async_engine(url, echo=echo)

    async def create_db_and_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    def get_session(self) -> DatabaseSession:
        return DatabaseSession(self.engine)
