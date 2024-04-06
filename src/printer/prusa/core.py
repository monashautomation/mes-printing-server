from pathlib import Path

import httpx
import rapidjson

from printer.core import BaseHttpPrinter
from printer.models import LatestJob, PrinterState, PrinterStatus, Temperature
from printer.prusa.models import CurrentJob, Status


def parse_state(state: str) -> PrinterState:
    match state.lower():
        case "idle" | "ready" | "finished" | "stopped" | "attention":
            return PrinterState.Ready
        case "printing" | "paused":
            return PrinterState.Printing
        case "error" | "busy":
            return PrinterState.Error
        case other:
            raise ValueError(other)


class PrusaPrinter(BaseHttpPrinter):
    async def connect(self) -> None:
        return

    async def current_status(self) -> PrinterStatus:
        url = self.url + "/api/v1/status"
        resp = await self.client.get(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

        model: Status = Status.model_validate_json(resp.text)

        printer = model.printer
        job = await self.latest_job()

        return PrinterStatus(
            state=parse_state(model.printer.state),
            temp_bed=Temperature(actual=printer.temp_bed, target=printer.target_bed),
            temp_nozzle=Temperature(
                actual=printer.temp_nozzle, target=printer.target_nozzle
            ),
            job=job,
        )

    async def upload_file(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        file = open(gcode_path, "rb")

        url = self.url + f"/api/v1/files/usb/{filename}"

        resp = await self.client.put(
            url,
            files={filename: file},
            headers={"Print-After-Upload": "0", "X-Api-Key": self.api_key},
        )
        resp.raise_for_status()

    async def delete_file(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        url = self.url + f"/api/v1/files/usb/{filename}"
        resp = await self.client.delete(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

    async def start_job(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        url = self.url + f"/api/v1/files/usb/{filename}"
        resp = await self.client.post(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

    async def stop_job(self) -> None:
        job = await self.latest_job()

        if job is None:
            return

        url = self.url + f"/api/v1/job/{job.id}"
        resp = await self.client.delete(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

    async def latest_job(self) -> LatestJob | None:
        url = self.url + "/api/v1/job"
        resp = await self.client.get(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

        if resp.status_code == httpx.codes.NO_CONTENT:
            return None

        data = rapidjson.loads(
            resp.text, parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS
        )
        model: CurrentJob = CurrentJob(**data)

        file = model.file
        assert file is not None

        return LatestJob(
            id=model.id,
            file_path=file.display_name,
            previewed_model_url=file.refs.thumbnail,
            progress=model.progress or 0.0,
            time_used=model.time_printing,
            time_left=model.time_remaining,
        )
