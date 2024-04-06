from pathlib import Path

from printer.core import BaseHttpPrinter
from printer.models import LatestJob, PrinterState, PrinterStatus, Temperature
from printer.octo.models import CurrentJob, OctoPrinterStatus, StateFlags


def parse_state(flags: StateFlags) -> PrinterState:
    if flags.ready:
        return PrinterState.Ready
    elif flags.printing or flags.paused:
        return PrinterState.Printing
    elif flags.error or flags.closedOrError:
        return PrinterState.Error
    else:
        raise ValueError


class OctoPrinter(BaseHttpPrinter):
    async def connect(self) -> None:
        url = self.url + "/api/connection"
        resp = await self.client.post(
            url, json={"command": "connect"}, headers={"X-Api-Key": self.api_key}
        )
        resp.raise_for_status()

    async def current_status(self) -> PrinterStatus:
        url = self.url + "/api/printer"
        resp = await self.client.get(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

        model: OctoPrinterStatus = OctoPrinterStatus.model_validate_json(resp.text)

        assert model.temperature is not None

        bed, noz = model.temperature.bed, model.temperature.tool0

        assert bed is not None and noz is not None

        job = await self.latest_job()

        return PrinterStatus(
            state=parse_state(model.state.flags),
            temp_bed=Temperature(actual=bed.actual or 0, target=bed.target or 0),
            temp_nozzle=Temperature(actual=bed.actual or 0, target=bed.target or 0),
            job=job,
        )

    async def upload_file(self, gcode_path: str) -> None:
        url = self.url + "/api/files/local"
        resp = await self.client.post(
            url,
            files={"file": open(gcode_path, "rb")},
            headers={"X-Api-Key": self.api_key},
        )
        resp.raise_for_status()

    async def delete_file(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        url = self.url + f"/api/files/local/{filename}"

        resp = await self.client.delete(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

    async def start_job(self, gcode_path: str) -> None:
        filename = Path(gcode_path).name
        url = self.url + f"/api/files/local/{filename}"

        resp = await self.client.post(
            url,
            json={"command": "select", "print": True},
            headers={"X-Api-Key": self.api_key},
        )
        resp.raise_for_status()

    async def stop_job(self) -> None:
        url = self.url + "/api/job"
        resp = await self.client.post(
            url, json={"command": "cancel"}, headers={"X-Api-Key": self.api_key}
        )
        resp.raise_for_status()

    async def latest_job(self) -> LatestJob | None:
        url = self.url + "/api/job"
        resp = await self.client.get(url, headers={"X-Api-Key": self.api_key})
        resp.raise_for_status()

        model: CurrentJob = CurrentJob.model_validate_json(resp.text)

        file = model.job.file

        if file is None or file.name is None:
            return None

        return LatestJob(
            file_path=file.name,
            progress=model.progress.completion,
            time_used=model.progress.printTime,
            time_left=model.progress.printTimeLeft,
            time_approx=model.job.estimatedPrintTime,
        )
