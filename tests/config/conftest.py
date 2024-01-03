from pathlib import Path

import pytest

from config.models import AppConfig
from db.models import Printer


def path_from_project_root(filename) -> Path:
    return Path() / "tests" / "config" / filename


def path_from_current_folder(filename) -> Path:
    return Path() / filename


def path_of(filename) -> str:
    path = path_from_project_root(filename)

    if not path.exists():
        path = path_from_current_folder(filename)

    return str(path)


@pytest.fixture
def env_filepath() -> str:
    return path_of(".env.unittest")


@pytest.fixture
def sqlite_filepath() -> str:
    return path_of("app.db")


@pytest.fixture
def app_config(sqlite_filepath) -> AppConfig:
    return AppConfig(
        DATABASE_URL=f"sqlite+aiosqlite:///{sqlite_filepath}",
        OPCUA_SERVER_URL="mock.opc.tcp://127.0.0.1:4840",
        UPLOAD_PATH="./gcode-files",
    )


@pytest.fixture
def prepare_env_file(app_config, env_filepath):
    lines = [
        f"DATABASE_URL='{app_config.db_url}'\n"
        f"OPCUA_SERVER_URL='{app_config.opcua_server_url}'\n"
        f"UPLOAD_PATH='{app_config.upload_path}'\n"
    ]
    with open(env_filepath, "w") as f:
        f.writelines(lines)


@pytest.fixture
def mock_printer() -> Printer:
    return Printer(octo_url="mock://localhost:5000", octo_api_key="foobar", opcua_ns=1)
