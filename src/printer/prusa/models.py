from pydantic import BaseModel


class PrusaPrinterStatus(BaseModel):
    state: str
    temp_nozzle: float
    target_nozzle: float
    temp_bed: float
    target_bed: float
    axis_x: float | None = None
    axis_y: float | None = None
    axis_z: float


class JobStatus(BaseModel):
    id: int | None = None
    progress: float | None = None
    time_remaining: int | None = None
    time_printing: int | None = None


class Status(BaseModel):
    job: JobStatus | None = None
    printer: PrusaPrinterStatus


class File(BaseModel):
    name: str
    display_name: str
    path: str


class CurrentJob(BaseModel):
    id: int
    file: File | None = None
    time_printing: int
    time_remaining: int | None = None


class FileUpload(BaseModel):
    name: str
    display_name: str
