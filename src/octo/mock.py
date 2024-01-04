from octo.core import BaseOctoClient
from octo.error import CannotPrint
from octo.models import (
    CurrentPrinterStatus,
    OctoPrinterStatus,
    PrinterState,
    PrinterStateFlags,
    TemperatureData,
    TemperatureState,
    CurrentJob,
    Job,
    File,
    Progress,
)


class PrintingJob:
    def __init__(self, job_file: str, required_ticks=10):
        self.job_file = job_file
        self.ticks = 0
        self.cancelled = False

        self.required_ticks = required_ticks
        self.progress_delta = 100 / required_ticks
        self.time_delta = 5

        self.progress = 0.0
        self.time_used = 0.0
        self.time_remain = self.time_delta * self.ticks

    def tick(self):
        self.ticks += 1

        if not self.cancelled and self.ticks <= self.required_ticks:
            self.progress = self.progress_delta * self.ticks
            self.time_used = self.time_delta * self.ticks
            self.time_remain = self.time_delta * (self.required_ticks - self.ticks)

    def is_printing(self):
        return not self.cancelled and self.progress < 100

    def is_finished(self):
        return not self.cancelled and self.progress == 100

    def is_cancelled(self):
        return self.cancelled

    def cancel(self):
        self.cancelled = True

    def _current_file(self):
        return File(
            name=self.job_file,
            display=self.job_file,
            path=self.job_file,
            type="machinecode",
            typePath=["machinecode", "gcode"],
        )

    def _current_progress(self):
        return Progress(
            completion=min(100.0, self.progress),
            printTime=self.time_used,
            printTimeLeft=max(0.0, self.time_remain),
        )

    def _current_state(self):
        if self.is_finished():
            return "Finished"
        elif self.is_cancelled():
            return "Cancelled"
        else:
            return OctoPrinterStatus.Printing

    def current_job(self):
        job = Job(estimatedPrintTime=200, file=self._current_file())

        return CurrentJob(
            state=self._current_state(), job=job, progress=self._current_progress()
        )


class Heater:
    def __init__(self, required_ticks=10, bed_target=200, nozzle_target=150):
        self.ticks = 0
        self.required_ticks = required_ticks

        self.bed_target: float = bed_target
        self.nozzle_target: float = nozzle_target

        self.bed_actual = 0.0
        self.nozzle_actual = 0.0

        self.bed_delta: float = bed_target / required_ticks
        self.nozzle_delta: float = nozzle_target / required_ticks

        self.heating = False

    def start_heating(self):
        self.heating = True

    def start_cooling(self):
        self.heating = False

    def tick(self):
        self.ticks += 1

        if self.heating:
            self.bed_actual = min(self.bed_target, self.bed_actual + self.bed_delta)
            self.nozzle_actual = min(
                self.nozzle_target, self.nozzle_actual + self.nozzle_delta
            )
        else:
            self.bed_actual = max(0.0, self.bed_actual - self.bed_delta)
            self.nozzle_actual = max(0.0, self.nozzle_actual - self.nozzle_delta)

    def is_ready(self):
        return (
            self.heating
            and self.nozzle_actual >= self.nozzle_target
            and self.bed_actual >= self.bed_target
        )

    def _bed_temperature(self) -> TemperatureData:
        return TemperatureData(target=self.bed_target, actual=self.bed_actual)

    def _nozzle_temperature(self):
        return TemperatureData(target=self.nozzle_target, actual=self.nozzle_actual)

    def current_temperature(self) -> TemperatureState:
        return TemperatureState(
            bed=self._bed_temperature(), tool0=self._nozzle_temperature()
        )


class MockOctoClient(BaseOctoClient):
    def __init__(self, url: str, api_key: str = "mock-api-key"):
        super().__init__(url, api_key)

        self.connected: bool = False

        self.state: OctoPrinterStatus = OctoPrinterStatus.Ready

        self.job: PrintingJob | None = None
        self.heater = Heater()

        # printer head
        self.head_xyz = [0, 0, 0]

        self.uploaded_files = set()

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def current_printer_status(self) -> CurrentPrinterStatus:
        status = CurrentPrinterStatus(
            state=self._current_printer_state(),
            temperature=self.heater.current_temperature(),
        )
        return status

    async def current_temperature(self) -> TemperatureState:
        return self.heater.current_temperature()

    async def upload_file_to_print(self, file_path: str) -> None:
        if self.state != OctoPrinterStatus.Ready:
            raise CannotPrint()

        self.state = OctoPrinterStatus.Printing
        self.job = PrintingJob(job_file=file_path)
        self.heater.start_heating()
        self.uploaded_files.add(file_path)

    async def current_job(self) -> CurrentJob:
        if self.job is None:
            return CurrentJob(
                state=OctoPrinterStatus.Operational, progress=Progress(), job=Job()
            )
        return self.job.current_job()

    async def cancel(self):
        if self.job is None:
            raise ValueError("no job to cancel")

        self.state = OctoPrinterStatus.Cancelling
        self.job.cancel()
        self.heater.start_cooling()

    async def head_jog(self, x: float, y: float, z: float):
        self.head_xyz = [x, y, z]

    def _current_printer_state(self) -> PrinterState:
        printer_state_flags = PrinterStateFlags(
            operational=True,
            ready=self.state == OctoPrinterStatus.Ready,
            printing=self.state == OctoPrinterStatus.Printing,
            cancelling=self.state == OctoPrinterStatus.Cancelling,
        )

        return PrinterState(text=self.state, flags=printer_state_flags)

    def tick(self):
        if self.job is None:
            self.heater.tick()
            return

        match self.job.is_printing(), self.heater.heating:
            case True, True:
                if self.heater.is_ready():
                    self.job.tick()
                else:
                    self.heater.tick()
            case False, True:
                self.heater.start_cooling()
                self.heater.tick()
            case False, False:
                self.heater.tick()  # cooling
            case True, False:
                raise ValueError("printer is cooling during printing")

        if not self.job.is_printing():
            self.state = OctoPrinterStatus.Ready

    async def delete_printed_file(self, file_path: str):
        self.uploaded_files.remove(file_path)
