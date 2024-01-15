from config import AppContext
from config.loader import (
    load_db,
    make_opcua_client,
    is_mocking,
    make_octo_client,
)
from db.models import Printer
from octo import MockOctoClient, OctoRestClient
from opcuax.core import OpcuaClient
from opcuax.mock import MockOpcuaClient


async def test_load_db(app_config, database):
    db = await load_db(app_config.db_url)
    assert str(db.engine.url) == app_config.db_url

    async with db.open_session() as session:
        printers = await session.all(Printer)
        assert printers != []


def test_is_mocking(app_config):
    assert is_mocking(app_config.opcua_server_url)
    assert not is_mocking("opc.tcp://127.0.0.1:4840")


def test_make_mock_opcua_client():
    url = "mock.opc.tcp://127.0.0.1:4840"
    client = make_opcua_client(url)
    assert isinstance(client, MockOpcuaClient)
    assert client.url == url


def test_make_opcua_client():
    url = "opc.tcp://127.0.0.1:4840"
    client = make_opcua_client(url)
    assert isinstance(client, OpcuaClient)
    assert client.url == url


async def test_make_mock_octo_client():
    url, api_key = "mock://localhost:5000", "foobar"
    client = await make_octo_client(url, api_key)
    assert isinstance(client, MockOctoClient)
    assert client.url == url
    assert client.api_key == api_key


async def test_make_octo_client():
    url, api_key = "http://localhost:5000", "foobar"
    client = await make_octo_client(url, api_key)
    assert isinstance(client, OctoRestClient)
    assert client.url == url
    assert client.api_key == api_key


async def test_load_app_context(prepare_env_file, database, app_config, printer1):
    ctx = AppContext()

    await ctx.load()

    assert str(ctx.db.engine.url) == app_config.db_url
    assert ctx.opcua_client.url == app_config.opcua_server_url
    assert len(ctx.printer_workers) == 1

    worker = ctx.printer_workers[0]

    assert worker.octo.url == printer1.octo_url
    assert worker.octo.api_key == printer1.octo_api_key
    assert worker.opcua_printer.client().url == app_config.opcua_server_url
    assert worker.opcua_printer.namespace() == printer1.opcua_ns

    await ctx.session.close()
    await ctx.db.close()
