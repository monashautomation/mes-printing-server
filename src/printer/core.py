from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, TypeVar
from urllib.parse import urljoin

from aiohttp import ClientSession
from pydantic import HttpUrl

from printer.models import LatestJob, PrinterStatus


class PrinterApi(StrEnum):
    OctoPrint = "OctoPrint"
    PrusaLink = "Prusa"
    Mock = "Mock"


class BaseActualPrinter(ABC):
    def __init__(self, url: str | HttpUrl, api_key: str | None = None):
        self.url: str = str(url)
        self.api_key: str = api_key

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

    async def __aenter__(self):
        await self.setup()
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


ActualPrinter = TypeVar("ActualPrinter", bound=BaseActualPrinter)


class BaseHttpPrinter(BaseActualPrinter, ABC):
    session: ClientSession

    def __init__(
        self, url: str | HttpUrl, session: ClientSession, api_key: str | None = None
    ) -> None:
        super().__init__(url, api_key)
        self.session = session

    def _request_params(
        self, endpoint: str, headers: dict[str, str] = None, **kwargs
    ) -> dict[str, Any]:
        h = {"X-Api-Key": self.api_key}
        if headers is not None:
            h.update(headers)
        return {
            "url": urljoin(self.url, endpoint),
            "headers": h,
        }

    def get(self, endpoint: str, **kwargs):
        return self.session.get(**self._request_params(endpoint), **kwargs)

    def post(self, endpoint: str, headers: dict[str, str] = None, **kwargs):
        return self.session.post(**self._request_params(endpoint, headers), **kwargs)

    def put(self, endpoint: str, headers: dict[str, str] = None, **kwargs):
        return self.session.put(**self._request_params(endpoint, headers), **kwargs)

    def delete(self, endpoint: str, **kwargs):
        return self.session.delete(**self._request_params(endpoint), **kwargs)
