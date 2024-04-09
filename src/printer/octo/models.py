from enum import StrEnum

from pydantic import BaseModel, Field


class State(StrEnum):
    Operational = "Operational"
    Paused = "Paused"
    Printing = "Printing"
    Pausing = "Pausing"
    Cancelling = "Cancelling"
    SdReady = "SdReady"
    Error = "Error"
    Ready = "Ready"
    ClosedOrError = "ClosedOrError"


class TemperatureData(BaseModel):
    actual: float = Field(description="Current temperature")
    target: float | None = Field(
        default=None,
        description="Target temperature, may be null if no target temperature is set.",
    )


class TemperatureState(BaseModel):
    tool0: TemperatureData | None = None
    tool1: TemperatureData | None = None
    tool2: TemperatureData | None = None
    bed: TemperatureData | None = None


class SDState(BaseModel):
    ready: bool


class StateFlags(BaseModel):
    operational: bool = False
    paused: bool = False
    printing: bool = False
    pausing: bool = False
    cancelling: bool = False
    sdReady: bool = False
    error: bool = False
    ready: bool = False
    closedOrError: bool = False


class PrinterState(BaseModel):
    text: State
    flags: StateFlags


class OctoPrinterStatus(BaseModel):
    state: PrinterState
    temperature: TemperatureState | None
    sd: SDState | None = None


class Filament(BaseModel):
    length: float | None = Field(
        default=None, description="Length of filament used, in mm"
    )
    volume: float | None = Field(
        default=None, description="Volume of filament used, in cm³"
    )


class File(BaseModel):
    name: str | None = Field(
        examples=["a_turtle_turtle.gco"],
        description="The name of the file without path",
        default=None,
    )

    path: str | None = Field(
        default=None,
        examples=["folder/subfolder/file.gco"],
        description="The path to the file within the location",
    )


class Job(BaseModel):
    file: File | None = Field(
        default=None, description="The file that is the target of the current print job"
    )
    estimatedPrintTime: float | None = Field(
        default=None, description="The estimated print time for the file, in seconds"
    )

    filament: Filament | None = Field(
        default=None,
        description="Information regarding the estimated filament usage of the print job",
    )


class Progress(BaseModel):
    completion: float | None = Field(
        default=None, description="Percentage of completion of the current print job"
    )
    filepos: int | None = Field(
        default=None,
        description="Current position in the file being printed, in bytes from the beginning",
    )
    printTime: int = Field(description="Time already spent printing, in seconds")
    printTimeLeft: int = Field(description="Estimate of time left to print, in seconds")


class CurrentJob(BaseModel):
    job: Job
    progress: Progress
    state: str
    error: str | None = None
