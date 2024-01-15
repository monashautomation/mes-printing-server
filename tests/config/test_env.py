import os

import pytest

from config.env import load_env, load_env_vars, load_env_file, EnvVar, AppConfig


@pytest.fixture
def clear_env_vars():
    config = {name: os.environ[name] for name in EnvVar if name in os.environ}

    for name in config:
        del os.environ[name]

    yield

    for name, val in config.items():
        os.environ[name] = val


@pytest.fixture
def env_vars():
    config = {
        EnvVar.db_url: "prod db url",
        EnvVar.opcua_server_url: "prod opcua url",
        EnvVar.upload_path: "prod upload path",
    }
    for name, val in config.items():
        os.environ[name] = val

    yield config

    for name in config:
        del os.environ[name]


@pytest.fixture
def env_config(env_vars):
    return AppConfig(**env_vars)


def test_load_env_vars(env_config):
    config = AppConfig(**load_env_vars())

    assert config == env_config


def test_load_missing_env_vars(clear_env_vars):
    assert load_env_vars() == {}


def test_load_env_file(prepare_env_file, env_path, app_config):
    config = AppConfig(**load_env_file(env_path))

    assert config == app_config


def test_load_missing_env_file():
    assert load_env_file(None) == {}


def test_load_env_from_env_file(clear_env_vars, prepare_env_file, env_path, app_config):
    config = load_env()

    assert config == app_config


def test_load_env_from_env_vars(env_config):
    config = load_env()

    assert config == env_config


def test_priority(prepare_env_file, env_path, env_config):
    config = load_env()

    assert config == env_config, "env vars should have higher priority than env file"
