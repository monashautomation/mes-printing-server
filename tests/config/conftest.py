from pathlib import Path

import pytest
import pytest_asyncio

from config.models import AppConfig
from db import Database
from db.models import Printer


@pytest.fixture
def folder(tmp_path) -> Path:
    return Path(tmp_path)


@pytest.fixture
def env_path(folder) -> str:
    path = folder / ".env"
    return str(path.absolute())


@pytest.fixture
def db_path(folder) -> str:
    path = folder / "app.db"
    return str(path.absolute())


@pytest.fixture
def app_config(db_path) -> AppConfig:
    return AppConfig(
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        OPCUA_SERVER_URL="mock.opc.tcp://127.0.0.1:4840",
        UPLOAD_PATH="./gcode-files",
    )


@pytest.fixture(autouse=True)
def prepare_env_file(app_config, env_path, tmp_path):
    lines = [
        f"DATABASE_URL='{app_config.db_url}'\n"
        f"OPCUA_SERVER_URL='{app_config.opcua_server_url}'\n"
        f"UPLOAD_PATH='{app_config.upload_path}'\n"
    ]
    with open(env_path, "w") as f:
        f.writelines(lines)


@pytest_asyncio.fixture
async def database(printer1, app_config):
    db = Database(app_config.db_url)
    await db.create_db_and_tables()

    session = db.open_session()
    await session.upsert(printer1)

    yield db

    await session.close()
    await db.close()


@pytest.fixture
def mock_printer() -> Printer:
    return Printer(octo_url="mock://localhost:5000", octo_api_key="foobar", opcua_ns=1)
