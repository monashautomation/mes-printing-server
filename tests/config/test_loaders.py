import pytest

from config import load_app_context
from config.loader import (
    load_db,
    load_env,
    make_opcua_client,
    is_mocking,
    make_octo_client,
)
from octo import MockOctoClient, OctoRestClient
from opcuax.client import OpcuaClient
from opcuax.mock import MockOpcuaClient


def test_load_env(prepare_env_file, env_filepath, app_config):
    config = load_env(env_filepath)

    assert config == app_config


@pytest.mark.asyncio
async def test_load_db(app_config):
    db = await load_db(app_config.db_url)
    assert db is not None
    assert str(db.engine.url) == app_config.db_url


def test_is_mocking(app_config):
    assert is_mocking(app_config.opcua_server_url)
    assert not is_mocking("opc.tcp://127.0.0.1:4840")


@pytest.mark.asyncio
async def test_make_mock_opcua_client():
    url = "mock.opc.tcp://127.0.0.1:4840"
    client = await make_opcua_client(url)
    assert isinstance(client, MockOpcuaClient)
    assert client.url == url


@pytest.mark.asyncio
async def test_make_opcua_client():
    url = "opc.tcp://127.0.0.1:4840"
    client = await make_opcua_client(url)
    assert isinstance(client, OpcuaClient)
    assert client.url == url


def test_make_mock_octo_client():
    url, api_key = "mock://localhost:5000", "foobar"
    client = make_octo_client(url, api_key)
    assert isinstance(client, MockOctoClient)
    assert client.url == url
    assert client.api_key == api_key


def test_make_octo_client():
    url, api_key = "http://localhost:5000", "foobar"
    client = make_octo_client(url, api_key)
    assert isinstance(client, OctoRestClient)
    assert client.url == url
    assert client.api_key == api_key


@pytest.mark.asyncio
async def test_load_app_context(
    prepare_env_file, env_filepath, app_config, mock_printer
):
    ctx = await load_app_context(env_filepath)

    assert str(ctx.db.engine.url) == app_config.db_url
    assert ctx.opcua_client.url == app_config.opcua_server_url
    assert len(ctx.printer_workers) == 1

    worker = ctx.printer_workers[0]

    assert worker.octo.url == mock_printer.octo_url
    assert worker.octo.api_key == mock_printer.octo_api_key
    assert worker.opcua_printer.client().url == app_config.opcua_server_url
    assert worker.opcua_printer.namespace() == mock_printer.opcua_ns
