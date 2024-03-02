from datetime import datetime
from enum import StrEnum
from pathlib import Path

from sqlmodel import Field, Relationship, SQLModel

from printer import PrinterApi


class Base(SQLModel):
    create_time: datetime = Field(default_factory=datetime.now)


class IntPK(Base):
    id: int | None = Field(primary_key=True, default=None)


class StrPK(Base):
    id: str | None = Field(primary_key=True, default=None)


class User(StrPK, table=True):
    name: str = Field(unique=True, index=True)
    permission: str = Field(description="admin/user")


class Printer(IntPK, table=True):
    url: str = Field(unique=True, description="Http URL of the printer")
    api_key: str | None = Field(description="API key of the printer")
    api: PrinterApi = Field(description="API standard")
    opcua_name: str = Field(description="browse name of the OPCUA server object")
    is_active: bool = Field(default=True)
    camera_url: str | None = Field(
        description="url of the camera attached to the printer"
    )
    model: str | None = Field(description="model of the printer")


class JobStatus(StrEnum):
    Pending = "pending"
    Printing = "printing"
    Printed = "printed"
    Storage = "storage"
    Finished = "finished"


class Order(IntPK, table=True):
    user_id: str = Field(foreign_key="user.id")
    printer_id: int | None = Field(foreign_key="printer.id", default=None)
    original_filename: str
    gcode_file_path: str
    job_status: JobStatus = Field(default=JobStatus.Pending)
    cancelled: bool = Field(default=False)
    approved: bool = Field(default=False)

    user: User | None = Relationship()
    printer: Printer | None = Relationship()

    def gcode_filename(self) -> str:
        return Path(self.gcode_file_path).name
