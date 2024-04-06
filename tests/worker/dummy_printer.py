from pydantic import HttpUrl

from printer.core import BaseActualPrinter
from printer.models import PrinterStatus, LatestJob


class DummyPrinter(BaseActualPrinter):
    def __init__(self, url: str | HttpUrl, api_key: str | None = None):
        super().__init__(url, api_key)
        self.files = set()
        self.current_job_file: str | None = None

    async def connect(self) -> None:
        return

    async def current_status(self) -> PrinterStatus:
        pass

    async def upload_file(self, gcode_path: str) -> None:
        self.files.add(gcode_path)

    async def delete_file(self, gcode_path: str) -> None:
        self.files.remove(gcode_path)

    async def start_job(self, gcode_path: str) -> None:
        self.current_job_file = gcode_path

    async def stop_job(self) -> None:
        self.current_job_file = None

    async def latest_job(self) -> LatestJob | None:
        pass
