from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel


class Temperature(BaseModel):
    actual: float
    target: float

    @property
    def heating_finished(self) -> bool:
        return self.actual >= self.target


class HeadPosition(BaseModel):
    x: float | None
    y: float | None
    z: float | None


class LatestJob(BaseModel):
    id: int | None = None
    file_path: str
    previewed_model_url: str | None = None
    # TODO remove None
    progress: float | None
    time_used: int  # seconds
    time_left: int
    time_approx: float | None = None

    @property
    def done(self) -> bool:
        return self.progress is not None and self.progress == 100

    @property
    def start_time(self) -> datetime:
        return datetime.now() - timedelta(seconds=self.time_used)


class PrinterState(StrEnum):
    Ready = "ready"
    Printing = "printing"
    Error = "error"


class PrinterStatus(BaseModel):
    state: PrinterState
    temp_bed: Temperature
    temp_nozzle: Temperature
    job: LatestJob | None = None

    @property
    def heating_finished(self) -> bool:
        return self.temp_bed.heating_finished and self.temp_nozzle.heating_finished

    @property
    def is_ready(self) -> bool:
        return self.state == PrinterState.Ready

    @property
    def is_printing(self) -> bool:
        return self.state == PrinterState.Printing

    @property
    def is_error(self) -> bool:
        return self.state == PrinterState.Error

    def job_progress_or_zero(self) -> float:
        if self.job is None:
            return 0
        return self.job.progress or 0
