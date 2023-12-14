import logging
from pathlib import Path

from aiohttp import ClientSession, FormData

from .models import CurrentPrinterStatus, CurrentJob, TemperatureState


class PrinterStateError(Exception):
    def __init__(self, *args):
        super().__init__("operation is not supported by current printer state", *args)


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
            match resp.status:
                case 204:
                    pass
                case 400:
                    raise ValueError("selected port or baudrate is not available")

    async def disconnect(self) -> None:
        async with self.session.post(
            "/api/connection", json={"command": "disconnect"}
        ) as resp:
            self.logger.info("disconnect %d", resp.status)
            match resp.status:
                case 204:
                    pass
                case 400:
                    raise ValueError("selected port or baudrate is not available")

    async def current_printer_status(self) -> CurrentPrinterStatus:
        async with self.session.get("/api/printer") as resp:
            self.logger.info("printer-status %d", resp.status)
            match resp.status:
                case 409:
                    raise PrinterStateError("Printer is not operational")
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
                    raise ValueError("Invalid axis specified")
                case 409:
                    raise PrinterStateError("Printer is not operational or is printing")

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
                    raise ValueError("invalid parameters")
                case 404:
                    raise ValueError(
                        "location is neither local nor sdcard, "
                        "or trying to upload to SD card and SD card support is disabled"
                    )
                case 409:
                    raise ValueError(
                        "the upload of the file would override the file that is currently being printed,"
                        "or an upload to SD card was requested and the printer is either not operational "
                        "or currently busy with a print job"
                    )
                case 415:
                    raise ValueError("file must be a gcode or stl")

    async def current_job(self) -> CurrentJob:
        async with self.session.get("/api/job") as resp:
            self.logger.info("job-info %d", resp.status)
            return CurrentJob.model_validate_json(await resp.text())

    async def cancel(self):
        async with self.session.post("/api/job", json={"command": "cancel"}) as resp:
            self.logger.info("cancel-job %d", resp.status)
            match resp.status:
                case 204:
                    pass
                case 409:
                    raise PrinterStateError(
                        "printer is not operational "
                        "or the current print job state does not match the preconditions for the command"
                    )
