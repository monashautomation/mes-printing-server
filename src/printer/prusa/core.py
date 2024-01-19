from pathlib import Path

from printer.core import BaseHttpPrinter
from printer.errors import Unauthorized, NotFound
from printer.models import LatestJob, PrinterStatus, Temperature, PrinterState
from printer.prusa.models import Status, CurrentJob


def parse_state(state: str) -> PrinterState:
    match state.lower():
        case "idle" | "ready" | "finished":
            return PrinterState.Ready
        case "printing":
            return PrinterState.Printing
        case "paused":
            return PrinterState.Paused
        case "stopped":
            return PrinterState.Stopped
        case "error":
            return PrinterState.Error
        case other:
            raise ValueError(other)


class PrusaPrinter(BaseHttpPrinter):
    async def connect(self) -> None:
        pass

    async def current_status(self) -> PrinterStatus:
        async with self.get("/api/v1/status") as resp:
            model: Status = await resp.json(loads=Status.model_validate_json)
            printer = model.printer
            job = await self.latest_job()

            return PrinterStatus(
                state=parse_state(model.printer.state),
                temp_bed=Temperature(
                    actual=printer.temp_bed, target=printer.target_bed
                ),
                temp_nozzle=Temperature(
                    actual=printer.temp_nozzle, target=printer.target_nozzle
                ),
                job=job,
            )

    async def upload_file(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        files = {"file": open(gcode_path, "rb")}

        async with self.post(f"/api/v1/files/local/{filename}", data=files) as resp:
            if resp.status != 201:
                raise ValueError

    async def delete_file(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name

        async with self.delete(f"/api/v1/files/local/{filename}") as resp:
            if resp.status != 204:
                raise ValueError

    async def start_job(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name

        async with self.post(f"/api/v1/files/local/{filename}") as resp:
            if resp.status != 204:
                raise ValueError

    async def stop_job(self) -> None:
        job = await self.latest_job()
        async with self.delete(f"/api/v1/job/{job.id}") as resp:
            match resp.status:
                case 204:
                    return
                case 401:
                    raise Unauthorized
                case 404:
                    raise NotFound
                case 409:
                    raise ValueError

    async def latest_job(self) -> LatestJob | None:
        async with self.get("/api/v1/job") as resp:
            if resp.status == 204:
                return None

            model: CurrentJob = await resp.json(loads=CurrentJob.model_validate_json)
            time_used, time_left = model.time_printing, model.time_remaining
            progress = None

            if time_left is not None:
                progress = time_used / (time_used + time_left)

            return LatestJob(
                id=model.id,
                file_path=model.file.name,
                progress=progress,
                time_used=model.time_printing,
                time_left=model.time_remaining,
            )
