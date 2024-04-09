from pydantic import BaseModel, Field


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


class FileRefs(BaseModel):
    icon: str = Field(examples=["/thumb/s/usb/ASSEM1~1.BGC"])
    thumbnail: str = Field(examples=["/thumb/l/usb/A~1.GCO"])
    download: str = Field(examples=["/usb/ASSEM1~1.BGC"])


class File(BaseModel):
    name: str
    display_name: str
    path: str
    refs: FileRefs


class CurrentJob(BaseModel):
    id: int
    state: str | None = None
    progress: float | None = None
    file: File | None = None
    time_printing: int
    time_remaining: int
