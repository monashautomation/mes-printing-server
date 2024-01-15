from db import Database
from db.models import Printer
from octo import OctoRestClient, MockOctoClient
from octo.core import BaseOctoClient
from opcuax.core import OpcuaClient
from opcuax.mock import MockOpcuaClient
from opcuax.objects import OpcuaPrinter
from worker import PrinterWorker


async def load_db(url: str) -> Database:
    db = Database(url=url)
    await db.create_db_and_tables()
    return db


def is_mocking(url: str):
    return url.startswith("mock")


def make_opcua_client(url: str) -> OpcuaClient:
    if is_mocking(url):
        return MockOpcuaClient(url=url)
    else:
        return OpcuaClient(url=url)


async def make_octo_client(url: str, api_key: str) -> BaseOctoClient:
    if is_mocking(url):
        return MockOctoClient(url=url, api_key=api_key)
    else:
        # aio.ClientSession must be initialized in an async function
        return OctoRestClient(url=url, api_key=api_key)


async def make_printer_worker(
    printer: Printer, db: Database, opcua_client: OpcuaClient
):
    opcua_printer = opcua_client.get_object(OpcuaPrinter, ns=printer.opcua_ns)
    octo_printer = await make_octo_client(printer.octo_url, printer.octo_api_key)

    return PrinterWorker(
        session=db.open_session(),
        opcua_printer=opcua_printer,
        octo=octo_printer,
        printer_id=printer.id,
    )
