import os
from pathlib import Path

import pytest

from setting import AppSettings, EnvAppSettings


@pytest.fixture
def set_env(settings: AppSettings):
    os.environ["DATABASE_URL"] = str(settings.database_url)
    os.environ["OPCUA_SERVER_URL"] = str(settings.opcua_server_url)
    os.environ["UPLOAD_PATH"] = str(settings.upload_path.absolute())

    yield

    del (
        os.environ["DATABASE_URL"],
        os.environ["OPCUA_SERVER_URL"],
        os.environ["UPLOAD_PATH"],
    )


def test_load_from_env_vars(settings: AppSettings, set_env):
    s = EnvAppSettings()

    assert s.database_url == settings.database_url
    assert s.opcua_server_url == settings.opcua_server_url
    assert s.upload_path == settings.upload_path
