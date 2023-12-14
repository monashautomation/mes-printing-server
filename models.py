from datetime import datetime
from enum import StrEnum
from typing import Optional, List

from sqlmodel import Field, SQLModel, Relationship


class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str
    permission: str = Field(description="admin/user")

    orders: List["Order"] = Relationship(back_populates="user")


class OrderStatus(StrEnum):
    Pending = "pending"
    Printing = "printing"
    Finished = "finished"
    Cancelled = "cancelled"


class Order(SQLModel, table=True):
    order_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    gcode_file_path: str
    create_time: datetime = Field(default=datetime.now())
    status: OrderStatus = Field(default=OrderStatus.Pending)
    approved: bool = Field(default=False)

    user: User = Relationship(back_populates="orders")
    job: Optional["Job"] = Relationship(back_populates="order")


class Job(SQLModel, table=True):
    job_id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.order_id")
    printer_ip: str
    start_time: datetime = Field(default=datetime.now())
    end_time: Optional[datetime]

    order: Order = Relationship(back_populates="job")
