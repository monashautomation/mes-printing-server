from pathlib import Path

from aiohttp import ClientSession
from pydantic_core import Url

from db import Database
from db.models import Printer
from opcuax.core import OpcuaClient
from opcuax.mock import MockOpcuaClient
from opcuax.objects import OpcuaPrinter
from printer import PrinterApi, OctoPrinter, PrusaPrinter, MockPrinter, ActualPrinter
from setting import AppSettings, EnvAppSettings
from worker import PrinterWorker


def _opcua_client(url: Url) -> OpcuaClient:
    if "mock" in url.host:
        return MockOpcuaClient(url=str(url))
    else:
        return OpcuaClient(url=str(url))


class AppContext:
    settings: AppSettings
    database: Database
    upload_path: Path
    opcua_client: OpcuaClient
    http_session: ClientSession
    workers: dict[int, PrinterWorker]

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.database = Database(settings.database_url)
        self.upload_path = settings.upload_path
        self.opcua_client = _opcua_client(settings.opcua_server_url)
        self.workers = {}

    @staticmethod
    def from_env() -> "AppContext":
        return AppContext(settings=EnvAppSettings())

    def actual_printer(self, printer: Printer) -> ActualPrinter:
        match printer.api:
            case PrinterApi.OctoPrint:
                return OctoPrinter(
                    url=printer.url, api_key=printer.api_key, session=self.http_session
                )
            case PrinterApi.PrusaLink:
                return PrusaPrinter(
                    url=printer.url, api_key=printer.api_key, session=self.http_session
                )
            case PrinterApi.Mock:
                return MockPrinter(
                    url=printer.url,
                    api_key=printer.api_key,
                    interval=self.settings.mock_printer_interval,
                    job_time=self.settings.mock_printer_job_time,
                )
            case _:
                raise NotImplemented

    def printer_worker(self, printer: Printer) -> PrinterWorker:
        opcua_printer = self.opcua_client.get_object(OpcuaPrinter, ns=printer.opcua_ns)
        actual_printer = self.actual_printer(printer)
        worker = PrinterWorker(
            session=self.database.new_session(),
            printer_id=printer.id,
            opcua_printer=opcua_printer,
            actual_printer=actual_printer,
            interval=self.settings.printer_worker_interval,
        )
        self.workers[printer.id] = worker
        return worker

    async def start_printer_workers(self) -> None:
        async with self.database.new_session() as session:
            printers = await session.active_printers()

            for printer in printers:
                worker = self.printer_worker(printer)
                worker.start()

    async def __aenter__(self):
        # ClientSession must be inited in an Awaitable
        self.http_session = ClientSession()
        await self.opcua_client.connect()
        await self.database.create_db_and_tables()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_session.close()
        await self.opcua_client.disconnect()
        await self.database.close()

        for worker in self.workers.values():
            worker.stop()
