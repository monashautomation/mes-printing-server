import asyncio
from asyncio import CancelledError, Task
from pathlib import Path

from pydantic import HttpUrl

from printer.core import BaseActualPrinter
from printer.errors import FileInUse, NotFound, PrinterIsBusy, Unauthorized
from printer.mock.models import _HeadPos, _Job
from printer.models import LatestJob, PrinterState, PrinterStatus, Temperature


class MockPrinter(BaseActualPrinter):
    def __init__(
        self,
        url: str | HttpUrl,
        api_key: str | None = None,
        interval: float = 1,
        job_time: int = 100,
        bed_expected: int = 150,
        nozzle_expected: int = 200,
    ):
        super().__init__(url, api_key)

        self.interval: float = interval

        self.connected = False
        self.state: PrinterState = PrinterState.Ready

        self.bed_actual = 0
        self.nozzle_actual = 0

        self.bed_expected = bed_expected
        self.nozzle_expected = nozzle_expected

        self.job_time: int = job_time
        self.jobs: list[_Job] = []
        self.files: set[str] = set()

        self.head_pos = _HeadPos(0, 0, 0)

        self.task: Task[None] | None = None

    async def setup(self) -> None:
        self.task = asyncio.create_task(self._run())

    async def cleanup(self) -> None:
        if self.task is not None:
            self.task.cancel()

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def current_status(self) -> PrinterStatus:
        self._check_connection()
        job = await self.latest_job()
        temp_bed = Temperature(actual=self.bed_actual, target=self.bed_expected)
        temp_noz = Temperature(actual=self.nozzle_actual, target=self.nozzle_expected)
        return PrinterStatus(
            state=self.state, job=job, temp_bed=temp_bed, temp_nozzle=temp_noz
        )

    async def upload_file(self, gcode_path: str) -> None:
        self._check_connection()

        if self._file_in_use(gcode_path):
            raise FileInUse

        self.files.add(Path(gcode_path).name)

    async def delete_file(self, gcode_path: str) -> None:
        self._check_connection()
        self._check_file_exists(gcode_path)

        if self._file_in_use(gcode_path):
            raise FileInUse

        self.files.remove(gcode_path)

    async def start_job(self, gcode_path: str) -> None:
        self._check_connection()
        self._check_file_exists(Path(gcode_path).name)

        if self._printing_job() is not None:
            raise PrinterIsBusy

        self.jobs.append(_Job(file=gcode_path, time_estimated=self.job_time))

    async def stop_job(self) -> None:
        self._check_connection()

        job = self._printing_job()

        if job is None:
            raise NotFound

        job.stopped = True

    async def latest_job(self) -> LatestJob | None:
        if len(self.jobs) == 0:
            return None

        job = self.jobs[-1]
        return LatestJob(
            file_path=job.file,
            progress=job.progress,
            time_used=job.time_used,
            time_left=job.time_left,
            time_approx=job.time_estimated,
        )

    def _check_connection(self) -> None:
        # 401 -> unauthorized
        if not self.connected:
            raise Unauthorized

    def _check_file_exists(self, gcode_path: str) -> None:
        if gcode_path not in self.files:
            raise NotFound

    def _file_in_use(self, gcode_path: str) -> bool:
        return gcode_path in (job.file for job in self.jobs if job.printing)

    def _printing_job(self) -> _Job | None:
        return next((job for job in self.jobs if job.printing), None)

    def _heating_finished(self) -> bool:
        return (
            self.bed_actual >= self.bed_expected
            and self.nozzle_actual >= self.nozzle_expected
        )

    def _update_states(self) -> None:
        job = self._printing_job()

        if job is None:
            self.state = PrinterState.Ready
            self.bed_actual = max(self.bed_actual - 10, 0)
            self.nozzle_actual = max(self.nozzle_actual - 10, 0)

        else:
            self.state = PrinterState.Printing
            self.bed_actual = min(self.bed_actual + 10, self.bed_expected)
            self.nozzle_actual = min(self.nozzle_actual + 10, self.nozzle_expected)

            if self._heating_finished():
                job.time_used += 1

    async def _run(self) -> None:
        try:
            while True:
                self._update_states()
                await asyncio.sleep(self.interval)
        except CancelledError:
            return
