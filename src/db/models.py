from datetime import datetime
from typing import Optional, Any

from sqlmodel import SQLModel, Field, Relationship


class Base(SQLModel):
    id: Optional[int] = Field(primary_key=True, default=None)
    create_time: datetime = Field(default=datetime.now())

    def __eq__(self, other: Any):
        return isinstance(other, self.__class__) and self.id == other.id


class User(Base, table=True):
    name: str = Field(unique=True, index=True)
    permission: str = Field(description="admin/user")


class Printer(Base, table=True):
    octo_url: str = Field(unique=True, description="URL of the octoprint server")
    octo_api_key: str = Field(description="API key of the octoprint server")
    opcua_ns: int = Field(description="namespace index of the OPCUA server object")


class Order(Base, table=True):
    user_id: int = Field(foreign_key="user.id")
    printer_id: Optional[int] = Field(foreign_key="printer.id", default=None)
    gcode_file_path: str

    approval_time: Optional[datetime] = Field(default=None)
    print_start_time: Optional[datetime] = Field(default=None)
    print_end_time: Optional[datetime] = Field(default=None)
    cancelled_time: Optional[datetime] = Field(default=None)
    finish_time: Optional[datetime] = Field(default=None)

    user: User = Relationship()
    printer: Optional[Printer] = Relationship()
