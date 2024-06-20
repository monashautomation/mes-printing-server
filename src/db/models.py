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
    # added 1-M relationships
    filament_status_histories: list["FilamentStatusHistory"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[FilamentStatusHistory.user_id]"},
    )
    filament_responsibilities_opened: list["FilamentResponsibility"] = Relationship(
        back_populates="opened_by_user",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.opened_by]"},
    )
    filament_responsibilities_assigned: list["FilamentResponsibility"] = Relationship(
        back_populates="assigned_to_user",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.assigned_to]"},
    )


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


# filament models


class Filament(SQLModel, table=True):
    filament_id: int | None = Field(default=None, primary_key=True)
    supplier: str | None = None
    material: str | None = None
    colour: str | None = None
    net_material: float | None = None
    barcode: str | None = None
    filament_left: float | None = None
    product: str | None = None
    waste: float | None = None
    timestamp: datetime | None = None
    filament_transaction: str | None = None
    allocated_weight: float | None = None

    filament_status_histories: list["FilamentStatusHistory"] = Relationship(
        back_populates="filament",
        sa_relationship_kwargs={"foreign_keys": "[FilamentStatusHistory.filament_id]"},
    )
    filament_responsibilities: list["FilamentResponsibility"] = Relationship(
        back_populates="filament",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.filament_id]"},
    )
    job_filaments: list["JobFilament"] = Relationship(
        back_populates="filament",
        sa_relationship_kwargs={"foreign_keys": "[JobFilament.filament_id]"},
    )


class FilamentStatusHistory(SQLModel, table=True):
    filament_history_id: int | None = Field(default=None, primary_key=True)
    printer_id: int | None = None
    user_id: int | None = Field(default=None, foreign_key="user.id")
    filament_id: int | None = Field(default=None, foreign_key="filament.filament_id")
    timestamp: datetime | None = None
    load_type: str | None = None
    spool_weight: float | None = None
    person: str | None = None

    user: User | None = Relationship(
        back_populates="filament_status_histories",
        sa_relationship_kwargs={"foreign_keys": "[FilamentStatusHistory.user_id]"},
    )
    filament: Filament | None = Relationship(
        back_populates="filament_status_histories",
        sa_relationship_kwargs={"foreign_keys": "[FilamentStatusHistory.filament_id]"},
    )


class FilamentResponsibility(SQLModel, table=True):
    filament_id: int | None = Field(
        default=None, primary_key=True, foreign_key="filament.filament_id"
    )
    opened_by: int | None = Field(default=None, foreign_key="user.id")
    assigned_to: int | None = Field(default=None, foreign_key="user.id")

    filament: Filament | None = Relationship(
        back_populates="filament_responsibilities",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.filament_id]"},
    )
    opened_by_user: User | None = Relationship(
        back_populates="filament_responsibilities_opened",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.opened_by]"},
    )
    assigned_to_user: User | None = Relationship(
        back_populates="filament_responsibilities_assigned",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.assigned_to]"},
    )


class JobFilament(SQLModel, table=True):
    filament_id: int | None = Field(
        default=None, foreign_key="filament.filament_id", primary_key=True
    )
    job_id: int | None = Field(default=None, primary_key=True)
    printer_id: int | None = None
    start: datetime | None = None
    end: datetime | None = None
    result: str | None = None
    part_weight: float | None = None
    waste: float | None = None
    estimated_g_code: str | None = None
    glue: str | None = None

    filament: Filament | None = Relationship(
        back_populates="job_filaments",
        sa_relationship_kwargs={"foreign_keys": "[JobFilament.filament_id]"},
    )
