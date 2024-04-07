import asyncio
import logging
from typing import Self


class PeriodicTask:
    def __init__(self, interval_secs: float, name: str | None = None):
        self.interval_secs: float = interval_secs
        self.name: str = name or type(self).__name__
        self.logger: logging.Logger = logging.getLogger(self.name)
        self.__stop: bool = False
        self.__task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.__task = asyncio.create_task(self.run())

    def stop(self) -> None:
        self.__stop = True
        self.__task = None

    async def run(self) -> None:
        self.logger.info("started")
        async with self:
            while not self.__stop:
                await self.step()
                await asyncio.sleep(self.interval_secs)
        self.logger.info("stopped")

    async def step(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return
