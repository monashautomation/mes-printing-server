from dataclasses import dataclass

from pydantic import BaseModel, Field

from db import Database, DatabaseSession
from opcuax.core import BaseOpcuaClient
from worker import PrinterWorker


class AppConfig(BaseModel):
    db_url: str = Field(alias="DATABASE_URL")
    opcua_server_url: str = Field(alias="OPCUA_SERVER_URL")
    upload_path: str = Field(alias="UPLOAD_PATH")


@dataclass
class AppContext:
    db: Database
    session: DatabaseSession
    opcua_client: BaseOpcuaClient
    printer_workers: list[PrinterWorker]
