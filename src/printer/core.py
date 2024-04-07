from abc import ABC, abstractmethod
from enum import StrEnum
from types import TracebackType
from typing import Self

from httpx import AsyncClient
from pydantic import HttpUrl

from printer.models import LatestJob, PrinterStatus


class PrinterApi(StrEnum):
    OctoPrint = "OctoPrint"
    PrusaLink = "Prusa"
    Mock = "Mock"


class BaseActualPrinter(ABC):
    def __init__(self, url: str | HttpUrl, api_key: str | None = None):
        self.url: str = str(url)
        self.api_key: str = api_key or ""

    async def setup(self) -> None:
        ...

    async def cleanup(self) -> None:
        ...

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def current_status(self) -> PrinterStatus:
        ...

    @abstractmethod
    async def upload_file(self, gcode_path: str) -> None:
        ...

    @abstractmethod
    async def delete_file(self, gcode_path: str) -> None:
        ...

    @abstractmethod
    async def start_job(self, gcode_path: str) -> None:
        ...

    @abstractmethod
    async def stop_job(self) -> None:
        ...

    @abstractmethod
    async def latest_job(self) -> LatestJob | None:
        ...

    async def __aenter__(self) -> Self:
        await self.setup()
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.cleanup()


Headers = dict[str, str]

client = AsyncClient()


class BaseHttpPrinter(BaseActualPrinter, ABC):
    def __init__(self, url: str | HttpUrl, api_key: str | None = None) -> None:
        super().__init__(url, api_key)
        self.client: AsyncClient = client
