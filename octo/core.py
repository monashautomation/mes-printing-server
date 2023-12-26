import logging
from pathlib import Path
from typing import TypeVar

from aiohttp import ClientSession, FormData

from octo.error import (
    InvalidConnectionParam,
    CannotPrint,
    InvalidAxis,
    InvalidUploadParam,
    InvalidUploadLocation,
    InvalidFileExtension,
)
from octo.models import CurrentPrinterStatus, CurrentJob, TemperatureState


class BaseOctoClient:
    def __init__(self, host: str, api_key: str, port: int = 5000):
        self.host = host
        self.api_key = api_key
        self.port = port

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def current_printer_status(self) -> CurrentPrinterStatus:
        pass

    async def current_temperature(self) -> TemperatureState:
        pass

    async def head_jog(self, x: float, y: float, z: float) -> None:
        pass

    async def upload_file_to_print(self, file_path: str) -> None:
        pass

    async def current_job(self) -> CurrentJob:
        pass

    async def cancel(self) -> None:
        pass


OctoprintClient = TypeVar("OctoprintClient", bound="BaseOctoClient")


class OctoRestClient(BaseOctoClient):
    def __init__(self, host: str, api_key: str, port: int = 5000):
        super().__init__(host, api_key, port)
        self.session: ClientSession = ClientSession(
            base_url=f"http://{host}:{port}", headers={"X-Api-Key": api_key}
        )
        self.logger = logging.getLogger(f"OctoClient {host}")

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        await self.close()

    async def connect(self) -> None:
        async with self.session.post(
            "/api/connection", json={"command": "connect"}
        ) as resp:
            self.logger.info("connect %d", resp.status)
            match resp.status:
                case 204:
                    pass
                case 400:
                    raise InvalidConnectionParam()

    async def disconnect(self) -> None:
        async with self.session.post(
            "/api/connection", json={"command": "disconnect"}
        ) as resp:
            self.logger.info("disconnect %d", resp.status)
            match resp.status:
                case 204:
                    pass
                case 400:
                    raise InvalidConnectionParam()

    async def current_printer_status(self) -> CurrentPrinterStatus:
        async with self.session.get("/api/printer") as resp:
            self.logger.info("printer-status %d", resp.status)
            match resp.status:
                case 409:
                    raise CannotPrint()
                case 200:
                    return CurrentPrinterStatus.model_validate_json(await resp.text())

    async def head_jog(self, x: float, y: float, z: float) -> None:
        async with self.session.post(
            "/api/printer/printhead", json={"command": "jog", "x": x, "y": y, "z": z}
        ) as resp:
            self.logger.info("printer-head %d", resp.status)
            match resp.status:
                case 204:
                    pass
                case 400:
                    raise InvalidAxis()
                case 409:
                    raise CannotPrint()

    async def current_temperature(self) -> TemperatureState:
        printer_status = await self.current_printer_status()
        return printer_status.temperature

    async def upload_file_to_print(self, file_path: str) -> None:
        form_data = FormData()
        form_data.add_field("select", "true")
        form_data.add_field("print", "true")
        form_data.add_field(
            "file",
            open(file_path, "rb"),
            filename=Path(file_path).name,
            content_type="application/octet-stream",
        )

        async with self.session.post("/api/files/local", data=form_data) as resp:
            self.logger.info("file-upload %d", resp.status)
            match resp.status:
                case 201:
                    pass
                case 400:
                    raise InvalidUploadParam()
                case 404:
                    raise InvalidUploadLocation()
                case 409:
                    raise CannotPrint()
                case 415:
                    raise InvalidFileExtension()

    async def current_job(self) -> CurrentJob:
        async with self.session.get("/api/job") as resp:
            self.logger.info("job-info %d", resp.status)
            return CurrentJob.model_validate_json(await resp.text())

    async def cancel(self) -> None:
        async with self.session.post("/api/job", json={"command": "cancel"}) as resp:
            self.logger.info("cancel-job %d", resp.status)
            match resp.status:
                case 204:
                    pass
                case 409:
                    raise CannotPrint()
