import asyncio
from pathlib import Path

from config.env import load_env
from config.loader import load_db, make_opcua_client, make_printer_worker
from db import Database, DatabaseSession
from db.models import Printer
from opcuax.core import OpcuaClient
from worker import PrinterWorker


class AppContext:
    db: Database
    session: DatabaseSession
    opcua_client: OpcuaClient
    printer_workers: list[PrinterWorker]
    upload_path: Path

    async def load(self):
        config = load_env()

        self.db = await load_db(config.db_url)
        self.session = self.db.open_session()
        printers = await self.session.all(Printer)
        self.opcua_client = make_opcua_client(url=config.opcua_server_url)
        self.printer_workers = [
            await make_printer_worker(p, self.db, self.opcua_client) for p in printers
        ]

    async def start_workers(self):
        async with asyncio.TaskGroup() as group:
            for worker in self.printer_workers:
                group.create_task(worker.run())

    async def close(self):
        await self.session.close()
        await self.db.close()
