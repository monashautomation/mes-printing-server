from dataclasses import dataclass

from pydantic import BaseModel, Field

from db import Database, DatabaseSession
from opcuax.core import OpcuaClient
from worker import PrinterWorker
from pathlib import Path


class AppConfig(BaseModel):
    db_url: str = Field(alias="DATABASE_URL")
    opcua_server_url: str = Field(alias="OPCUA_SERVER_URL")
    upload_path: str = Field(alias="UPLOAD_PATH")


@dataclass
class AppContext:
    db: Database
    session: DatabaseSession
    opcua_client: OpcuaClient
    printer_workers: list[PrinterWorker]
    upload_path: Path
