from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlmodel import Field, Relationship, SQLModel

from printer import PrinterApi


class Base(SQLModel):
    id: int | None = Field(primary_key=True, default=None)
    create_time: datetime = Field(default_factory=datetime.now)

    def __eq__(self, other: Any):
        if not isinstance(other, type(self)) or self.id is None:
            return False
        return self.id == other.id


class User(Base, table=True):
    id: str | None = Field(primary_key=True, default=None)
    name: str = Field(unique=True, index=True)
    permission: str = Field(description="admin/user")


class Printer(Base, table=True):
    url: str = Field(unique=True, description="Http URL of the printer")
    api_key: str | None = Field(description="API key of the printer")
    api: PrinterApi = Field(description="API standard")
    opcua_ns: int = Field(description="namespace index of the OPCUA server object")
    is_active: bool = Field(default=True)


class JobStatus(StrEnum):
    Pending = "pending"
    Printing = "printing"
    Printed = "printed"
    Storage = "storage"
    Finished = "finished"


class Order(Base, table=True):
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
