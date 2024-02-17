from pathlib import Path

import rapidjson

from printer.core import BaseHttpPrinter
from printer.errors import FileAlreadyExists, FileInUse, NotFound, Unauthorized
from printer.models import LatestJob, PrinterState, PrinterStatus, Temperature
from printer.prusa.models import CurrentJob, Status


def parse_state(state: str) -> PrinterState:
    match state.lower():
        case "idle" | "ready" | "finished" | "stopped" | "attention":
            return PrinterState.Ready
        case "printing" | "paused":
            return PrinterState.Printing
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
        file = open(gcode_path, "rb")

        # TODO: make sure storage is usb
        async with self.put(
            f"/api/v1/files/usb/{filename}",
            data=file,
            headers={"Print-After-Upload": "0"},
        ) as resp:
            print(f"debug - upload file {resp.status}")
            match resp.status:
                case 201 | 204:
                    return None
                case 404:
                    raise NotFound
                case 409:
                    raise FileAlreadyExists
                case 422:
                    raise ValueError

    async def delete_file(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name

        async with self.delete(f"/api/v1/files/usb/{filename}") as resp:
            match resp.status:
                case 204:
                    return
                case 404:
                    raise NotFound
                case 409:
                    raise FileInUse

    async def start_job(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name

        async with self.post(f"/api/v1/files/usb/{filename}") as resp:
            match resp.status:
                case 204:
                    return
                case 401:
                    raise Unauthorized
                case 404:
                    raise NotFound
                case 409:
                    raise ValueError

    async def stop_job(self) -> None:
        job = await self.latest_job()

        if job is None:
            return

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

            # json response may have trailing commas
            text = await resp.text()
            data = rapidjson.loads(
                text, parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS
            )
            model: CurrentJob = CurrentJob(**data)

            time_used, time_left = model.time_printing, model.time_remaining
            file = model.file

            assert file is not None

            progress = 0.0

            if time_left is not None and (time_used + time_left) > 0:
                progress = time_used / (time_used + time_left)

            return LatestJob(
                id=model.id,
                file_path=file.display_name,
                progress=progress,
                time_used=model.time_printing,
                time_left=model.time_remaining,
            )
