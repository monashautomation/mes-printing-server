# filament models
from sqlmodel import Field, Relationship, SQLModel
from models import User
from datetime import datetime
from typing import Optional


class UserFilament(SQLModel, table=True):
    id: str | None = Field(primary_key=True, default=None)
    email: str = Field(unique=True, index=True)
    name: str = Field(unique=True)
    permission: str = Field(description="admin/user")
    user: "User" = Relationship(back_populates="user_filament", uselist=False)
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

    # some helper methods
    def has_filament_user(self) -> bool:
        """Check if the user has associated UserFilament."""
        return self.user_filament is not None

    def get_filament_user_details(self) -> Optional["UserFilament"]:
        """Get the UserFilament details associated with the user."""
        return self.user_filament

    def get_filament_user_id(self) -> str | None:
        """Get the ID of the UserFilament associated with the user."""
        return self.user_filament.id if self.user_filament else None


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


class FilamentResponsibility(SQLModel, table=True):
    filament_id: int | None = Field(
        default=None, primary_key=True, foreign_key="filament.filament_id"
    )
    opened_by: int | None = Field(default=None, foreign_key="UserFilament.id")
    assigned_to: int | None = Field(default=None, foreign_key="UserFilament.id")

    filament: Filament | None = Relationship(
        back_populates="filament_responsibilities",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.filament_id]"},
    )
    opened_by_user: UserFilament | None = Relationship(
        back_populates="filament_responsibilities_opened",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.opened_by]"},
    )
    assigned_to_user: UserFilament | None = Relationship(
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


class FilamentStatusHistory(SQLModel, table=True):
    filament_history_id: int | None = Field(default=None, primary_key=True)
    printer_id: int | None = None
    user_id: int | None = Field(default=None, foreign_key="UserFilament.id")
    filament_id: int | None = Field(default=None, foreign_key="filament.filament_id")
    timestamp: datetime | None = None
    load_type: str | None = None
    spool_weight: float | None = None
    person: str | None = None

    user: UserFilament | None = Relationship(
        back_populates="filament_status_histories",
        sa_relationship_kwargs={"foreign_keys": "[FilamentStatusHistory.user_id]"},
    )
    filament: Filament | None = Relationship(
        back_populates="filament_status_histories",
        sa_relationship_kwargs={"foreign_keys": "[FilamentStatusHistory.filament_id]"},
    )

    filament_responsibilities_opened: list[FilamentResponsibility] = Relationship(
        back_populates="opened_by_user",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.opened_by]"},
    )

    filament_responsibilities_assigned: list[FilamentResponsibility] = Relationship(
        back_populates="assigned_to_user",
        sa_relationship_kwargs={"foreign_keys": "[FilamentResponsibility.assigned_to]"},
    )
