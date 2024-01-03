from datetime import datetime
from enum import StrEnum
from typing import Optional, List, Any

from sqlalchemy import String, ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship


class Base(AsyncAttrs, DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(server_default=func.now())

    def __eq__(self, other: Any):
        return isinstance(other, self.__class__) and self.id == other.id


class User(Base):
    __tablename__ = "user"

    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    permission: Mapped[str] = mapped_column(String(16), comment="admin/user")

    orders: Mapped[List["Order"]] = relationship(back_populates="user")

    def __repr__(self):
        return f"User(id={self.id}, name={self.name}, permission={self.permission}, create_time={repr(self.create_time)})"


class OrderStatus(StrEnum):
    Approved = "approved"
    Printing = "printing"
    Printed = "printed"
    Inventory = "inventory"
    Cancelling = "cancelling"
    Finish = "finish"


class Order(Base):
    __tablename__ = "order"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    gcode_file_path: Mapped[str]
    printer_ip: Mapped[Optional[str]]

    approval_time: Mapped[Optional[datetime]]
    print_start_time: Mapped[Optional[datetime]]
    print_end_time: Mapped[Optional[datetime]]
    cancelled_time: Mapped[Optional[datetime]]
    finish_time: Mapped[Optional[datetime]]

    user: Mapped[User] = relationship(back_populates="orders")

    def __repr__(self):
        return (
            f"Order(id={self.id}, user_id={self.user_id}, gcode_file_path={self.gcode_file_path}, "
            f"printer_ip={self.printer_ip}, create_time={repr(self.create_time)},"
            f"approval_time={self.approval_time}, print_start_time={self.print_start_time},"
            f"print_end_time={self.print_end_time}, cancelled_time={self.cancelled_time},"
            f"finish_time={self.finish_time})"
        )


class Printer(Base):
    __tablename__ = "printer"

    octo_url: Mapped[str] = mapped_column(
        unique=True, comment="URL of the octoprint server"
    )
    octo_api_key: Mapped[str] = mapped_column(comment="API key of the octoprint server")
    opcua_ns: Mapped[int] = mapped_column(
        comment="namespace index of the OPCUA server object"
    )
