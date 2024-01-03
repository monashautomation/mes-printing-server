from dotenv import dotenv_values

from config.models import AppConfig, AppContext
from db import Database
from db.models import Printer
from octo import OctoRestClient, MockOctoClient
from octo.core import BaseOctoClient
from opcuax.core import OpcuaClient
from opcuax.mock import MockOpcuaClient
from opcuax.objects import OpcuaPrinter
from worker import PrinterWorker


def load_env(env_filepath: str = ".env") -> AppConfig:
    return AppConfig(**dotenv_values(env_filepath))


async def load_db(url: str) -> Database:
    db = Database(url=url)
    await db.create_db_and_tables()
    return db


def is_mocking(url: str):
    return url.startswith("mock")


async def make_opcua_client(url: str) -> OpcuaClient:
    if is_mocking(url):
        return MockOpcuaClient(url=url)
    else:
        # OpcuaClient::client must be initialized in an async function
        return OpcuaClient(url=url)


def make_octo_client(url: str, api_key: str) -> BaseOctoClient:
    if is_mocking(url):
        return MockOctoClient(url=url, api_key=api_key)
    else:
        return OctoRestClient(url=url, api_key=api_key)


def make_printer_worker(printer: Printer, db: Database, opcua_client: OpcuaClient):
    opcua_printer = opcua_client.get_object(OpcuaPrinter, ns=printer.opcua_ns)
    octo_printer = make_octo_client(printer.octo_url, printer.octo_api_key)

    return PrinterWorker(
        session=db.open_session(), opcua_printer=opcua_printer, octo=octo_printer
    )


async def load_app_context(env_filepath: str = ".env") -> AppContext:
    config = load_env(env_filepath)

    db = await load_db(config.db_url)
    session = db.open_session()
    printers = await session.all(Printer)
    opcua_client = await make_opcua_client(url=config.opcua_server_url)
    workers = [make_printer_worker(p, db, opcua_client) for p in printers]

    return AppContext(
        db=db, session=session, opcua_client=opcua_client, printer_workers=workers
    )
