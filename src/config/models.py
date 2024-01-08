from dataclasses import dataclass
from pathlib import Path

from db import Database, DatabaseSession
from opcuax.core import OpcuaClient
from worker import PrinterWorker


@dataclass
class AppContext:
    db: Database
    session: DatabaseSession
    opcua_client: OpcuaClient
    printer_workers: list[PrinterWorker]
    upload_path: Path
