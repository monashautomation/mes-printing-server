from pathlib import Path

from printer.core import BaseHttpPrinter
from printer.errors import NotFound, FileInUse, PrinterIsBusy
from printer.models import LatestJob, PrinterStatus, Temperature, PrinterState
from printer.octo.models import OctoPrinterStatus, CurrentJob, StateFlags


def parse_state(flags: StateFlags) -> PrinterState:
    if flags.ready:
        return PrinterState.Ready
    elif flags.printing:
        return PrinterState.Printing
    elif flags.paused:
        return PrinterState.Paused
    elif flags.error or flags.closedOrError:
        return PrinterState.Error
    else:
        raise ValueError


class OctoPrinter(BaseHttpPrinter):
    async def connect(self) -> None:
        async with self.post("/api/connection", json={"command": "connect"}) as resp:
            if resp.status == 400:
                raise ValueError

    async def current_status(self) -> PrinterStatus:
        async with self.get("/api/printer") as resp:
            if resp.status != 200:
                raise RuntimeError
            model: OctoPrinterStatus = await resp.json(
                loads=OctoPrinterStatus.model_validate_json
            )
            bed, noz = model.temperature.bed, model.temperature.tool0

            job = await self.latest_job()

            return PrinterStatus(
                state=parse_state(model.state.flags),
                temp_bed=Temperature(actual=bed.actual, target=bed.target),
                temp_nozzle=Temperature(actual=bed.actual, target=bed.target),
                job=job,
            )

    async def upload_file(self, gcode_path: str) -> None:
        files = {"file": open(gcode_path, "rb")}

        async with self.post("/api/files/local", data=files) as resp:
            if resp.status != 201:
                raise ValueError

    async def delete_file(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        url = f"/api/files/local/{filename}"

        async with self.delete(url) as resp:
            match resp.status:
                case 204:
                    return
                case 404:
                    raise NotFound
                case 409:
                    raise FileInUse

    async def start_job(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        url = f"/api/files/local/{filename}"

        async with self.post(url, json={"command": "select", "print": True}) as resp:
            match resp.status:
                case 200 | 202 | 204:
                    return
                case 404:
                    raise NotFound
                case 409:
                    raise PrinterIsBusy

    async def stop_job(self) -> None:
        async with self.post("/api/job", json={"command": "cancel"}) as resp:
            match resp.status:
                case 204:
                    return
                case 409:
                    raise NotFound

    async def latest_job(self) -> LatestJob | None:
        async with self.get("/api/job") as resp:
            model: CurrentJob = await resp.json(loads=CurrentJob.model_validate_json)

            if model.job.file.name is None:
                return None

            time_used = model.progress.printTime

            return LatestJob(
                file_path=model.job.file.name,
                progress=model.progress.completion,
                time_used=time_used,
                time_left=model.progress.printTimeLeft,
                time_approx=model.job.estimatedPrintTime,
            )
