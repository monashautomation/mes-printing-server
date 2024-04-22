from datetime import datetime
from enum import Flag
from pathlib import Path

from sqlmodel import Field, Relationship, SQLModel

from printer import PrinterApi


class Base(SQLModel):
    """
    Common fields of all tables
    """

    create_time: datetime = Field(default_factory=datetime.now)


class IntPK(Base):
    id: int | None = Field(primary_key=True, default=None)


class User(SQLModel, table=True):
    id: str | None = Field(primary_key=True, default=None)
    email: str = Field(unique=True, index=True)
    name: str = Field(unique=True)
    permission: str = Field(description="admin/user")


class Printer(IntPK, table=True):
    url: str = Field(unique=True, description="HTTP URL of the printer")
    api_key: str | None = Field(description="API key of the printer")
    api: PrinterApi = Field(description="API standard")
    group_name: str | None = Field(
        index=True, default="default", description="name of the printer group"
    )
    has_worker: bool = Field(
        default=True, description="whether a PrinterWorker is monitoring this printer"
    )
    opcua_name: str | None = Field(description="browse name of the OPCUA server object")
    camera_url: str | None = Field(
        description="url of the camera attached to the printer"
    )
    model: str | None = Field(description="model of the printer, e.g. Prusa XL")


class Order(IntPK, table=True):
    user_id: str = Field(foreign_key="user.id")
    printer_id: int | None = Field(foreign_key="printer.id", default=None)
    cancelled: bool = Field(default=False)

    user: User | None = Relationship()
    printer: Printer | None = Relationship()


class JobStatus(Flag):
    Created = 1
    Approved = 2
    Scheduled = 4
    Printing = 8
    Printed = 16
    Picked = 256
    Cancelled = 512
    PickupIssued = 1024
    CancelIssued = 2048

    ToSchedule = Created | Approved
    ToPrint = ToSchedule | Scheduled


class Job(IntPK, table=True):
    # a job may not have an order id or user id if it is submitted to the printer directly
    order_id: int | None = Field(foreign_key="order.id", default=None)
    user_id: str | None = Field(foreign_key="user.id", default=None)
    printer_id: int | None = Field(foreign_key="printer.id", default=None)
    status: int = Field(default=JobStatus.Created.value)
    from_server: bool
    gcode_file_path: str | None = Field(default=None)
    original_filename: str | None = Field(default=None)
    printer_filename: str | None = Field(default=None)
    start_time: datetime | None = Field(default=None)

    def add_status_flag(self, status: JobStatus) -> None:
        self.status |= status.value

    def flag(self) -> JobStatus:
        return JobStatus(self.status)

    def gcode_filename(self) -> str | None:
        if self.gcode_file_path is None:
            return None

        return Path(self.gcode_file_path).name

    def need_cancel(self) -> bool:
        stat = self.flag()
        return JobStatus.CancelIssued in stat and JobStatus.Cancelled not in stat

    def need_pickup(self) -> bool:
        stat = self.flag()
        return JobStatus.Printed in stat and JobStatus.PickupIssued not in stat

    def is_printing(self) -> bool:
        return (
            JobStatus.Printing in self.flag() and self.status < JobStatus.Printed.value
        )

    def is_printed(self) -> bool:
        return JobStatus.Printed in self.flag()

    def is_picked(self) -> bool:
        return JobStatus.Picked in self.flag()

    def is_pending(self) -> bool:
        return self.flag() == JobStatus.ToPrint


class JobHistory(IntPK, table=True):
    job_id: int = Field(foreign_key="job.id")
    status: str


class Filament(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    supplier: str = Field(description="Supplier")
    material: str = Field(description="Material type")
    color: str = Field(description="Filament color")
    net_material: float = Field(description="Net material")
    barcode: str = Field(description="Barcode")
    allocated_to: str = Field(description="allocation")
    opened_by: str = Field(description="Who opened the filament")
    opened_on: datetime = Field(description="Opened timestamp")
    weight: float = Field(description="Total weight including spool")
    filament_left: float = Field(default=0, description="Remaining filament")
    filament_waste: float = Field(default=0, description="Wasted filament")
