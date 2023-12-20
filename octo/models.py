from enum import StrEnum

from pydantic import BaseModel, Field


class OctoPrinterStatus(StrEnum):
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
    offset: float | None = Field(
        default=None,
        description="Currently configured temperature offset to apply, "
        "will be left out for historic temperature information.",
    )


class TemperatureState(BaseModel):
    tool0: TemperatureData | None = Field(
        default=None, description="Current temperature stats for tool 0"
    )
    tool1: TemperatureData | None = Field(
        default=None, description="Current temperature stats for tool 1"
    )
    tool2: TemperatureData | None = Field(
        default=None, description="Current temperature stats for tool 2"
    )
    bed: TemperatureData = Field(
        default=None,
        description="Current temperature stats for the printer’s heated bed. "
        "Not included if querying only tool state "
        "or if the currently selected printer profile does not have a heated bed.",
    )


class SDState(BaseModel):
    ready: bool = Field(description="Whether the SD card has been initialized")


class PrinterStateFlags(BaseModel):
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
    text: OctoPrinterStatus = Field(
        description="A textual representation of the current state of the printer"
    )
    flags: PrinterStateFlags = Field(description="A few boolean printer state flags")


class CurrentPrinterStatus(BaseModel):
    temperature: TemperatureState | None = Field(
        description="The printer’s temperature state data"
    )
    sd: SDState | None = Field(default=None, description="The printer’s sd state data")
    state: PrinterState | None = Field(description="The printer’s general state")


class Filament(BaseModel):
    length: float | None = Field(
        default=None, description="Length of filament used, in mm"
    )
    volume: float | None = Field(
        default=None, description="Volume of filament used, in cm³"
    )


class File(BaseModel):
    name: str = Field(
        examples=["a_turtle_turtle.gco"],
        description="The name of the file without path. "
        "E.g. “file.gco” for a file “file.gco” located anywhere in the file system. "
        "Currently this will always fit into ASCII.",
    )
    display: str = Field(
        default=None,
        examples=["a turtle 🐢.gco"],
        description="The name of the file without the path, this time potentially with non-ASCII unicode characters. "
        "E.g. “a turtle 🐢.gco” for a file “a_turtle_turtle.gco” located anywhere in the file system.",
    )
    path: str = Field(
        default=None,
        examples=["folder/subfolder/file.gco"],
        description="The path to the file within the location. "
        "E.g. “folder/subfolder/file.gco” for a file “file.gco” "
        "located within “folder” and “subfolder” relative to the root of the location. "
        "Currently this will always fit into ASCII.",
    )
    type: str = Field(
        default=None,
        examples=["model", "machinecode", "folder"],
        description="Type of file. model or machinecode. "
        "Or folder if it’s a folder, in which case the children node will be populated",
    )
    type_path: list[str] | None = Field(
        default=None,
        alias="typePath",
        examples=[["machinecode", "gcode"], ["model", "stl"], ["folder"]],
        description="Path to type of file in extension tree. "
        'E.g. ["model", "stl"] for .stl files, or ["machinecode", "gcode"] for .gcode files. ["folder"] for folders.',
    )


class Job(BaseModel):
    file: File = Field(
        description="The file that is the target of the current print job"
    )
    estimatedPrintTime: float | None = Field(
        default=None, description="The estimated print time for the file, in seconds."
    )
    lastPrintTime: float | None = Field(
        default=None,
        description="The print time of the last print of the file, in seconds.",
    )
    filament: Filament | None = Field(
        default=None,
        description="Information regarding the estimated filament usage of the print job",
    )


class Progress(BaseModel):
    completion: float = Field(
        description="Percentage of completion of the current print job"
    )
    filepos: int = Field(
        default=0,
        description="Current position in the file being printed, in bytes from the beginning",
    )
    printTime: int = Field(description="Time already spent printing, in seconds")
    printTimeLeft: int = Field(description="Estimate of time left to print, in seconds")
    printTimeLeftOrigin: str | None = Field(
        default=None,
        description="Origin of the current time left estimate. Can currently be either of:"
        "linear, analysis, estimate, average, mixed-analysis, mixed-average",
    )


class CurrentJob(BaseModel):
    job: Job = Field(
        description="Information regarding the target of the current print job"
    )
    progress: Progress = Field(
        description="Information regarding the progress of the current print job"
    )
    state: str = Field(
        description="A textual representation of the current state of the job or connection, "
        "e.g. “Operational”, “Printing”, “Pausing”, “Paused”, “Cancelling”, “Error”, "
        "“Offline”, “Offline after error”, “Opening serial connection”, … – "
        "please note that this list is not exhaustive!"
    )
    error: str | None = Field(
        default=None,
        description="Any error message for the job or connection, only set if there has been an error.",
    )
