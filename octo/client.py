import logging
from pathlib import Path

from aiohttp import ClientSession, FormData

from models import CurrentPrinterStatus, CurrentJob, TemperatureState


class OctoClient:
    def __init__(self, host: str, api_key: str, port: int = 5000):
        self.host: str = host
        self.session: ClientSession = ClientSession(
            base_url=f"http://{host}:{port}", headers={"X-Api-Key": api_key}
        )
        self.logger = logging.getLogger(f"OctoClient {host}")

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self) -> None:
        async with self.session.post(
            "/api/connection", json={"command": "connect"}
        ) as resp:
            self.logger.info("connect %d", resp.status)

    async def disconnect(self) -> None:
        async with self.session.post(
            "/api/connection", json={"command": "disconnect"}
        ) as resp:
            self.logger.info("disconnect %d", resp.status)

    async def current_printer_status(self) -> CurrentPrinterStatus:
        async with self.session.get("/api/printer") as resp:
            self.logger.info("printer-status %d", resp.status)
            return CurrentPrinterStatus.model_validate_json(await resp.text())

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

    async def current_job(self) -> CurrentJob:
        async with self.session.get("/api/job") as resp:
            return CurrentJob.model_validate_json(await resp.text())

    async def head_jog(self, x: float, y: float, z: float) -> None:
        async with self.session.post(
            "/api/printer/printhead", json={"command": "jog", "x": x, "y": y, "z": z}
        ) as resp:
            self.logger.info("printer-head %d", resp.status)

    async def cancel(self):
        async with self.session.post("/api/job", json={"command": "cancel"}) as resp:
            self.logger.info("cancel-job %d", resp.status)
