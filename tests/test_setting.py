import os

import pytest

from setting import AppSettings, EnvAppSettings, app_settings


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


def test_load_env_app_settings(settings: AppSettings, set_env):
    s = EnvAppSettings()

    assert s.database_url == settings.database_url
    assert s.opcua_server_url == settings.opcua_server_url
    assert s.upload_path == settings.upload_path


def test_app_settings_is_set() -> None:
    assert app_settings is not None


def test_override_app_settings() -> None:
    db_url = "sqlite:///test.db"
    app_settings.database_url = db_url
    assert str(app_settings.database_url) == db_url
