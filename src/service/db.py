from db import DatabaseSession, session
from typing import Self


class BaseDbService:
    def __init__(self, db: DatabaseSession | None = None) -> None:
        """
        Init by setting up a database session.

        Since using one database session in multiple asyncio tasks will cause concurrency issues,
        the service reuses an existing session from the caller if it is local to a task,
        or it creates a new session.

        The caller should ensure all service instances are not shared by multiple asyncio tasks.
        :param db: a database session, the service will use a new session if is None
        """
        self.mange_session: bool = db is None
        self.db: DatabaseSession = db or session()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.mange_session:
            await self.db.close()
