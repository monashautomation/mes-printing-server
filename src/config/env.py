import os
from enum import StrEnum

from dotenv import dotenv_values
from pydantic import BaseModel, Field


class EnvVar(StrEnum):
    db_url = "DATABASE_URL"
    opcua_server_url = "OPCUA_SERVER_URL"
    upload_path = "UPLOAD_PATH"
    env_file = "ENV_FILE"


class AppConfig(BaseModel):
    db_url: str = Field(alias=EnvVar.db_url)
    opcua_server_url: str = Field(alias=EnvVar.opcua_server_url)
    upload_path: str = Field(alias=EnvVar.upload_path)


def load_env_file(env_filepath: str | None = None) -> dict[str, str]:
    if env_filepath is None:
        return {}
    else:
        return dotenv_values(env_filepath)


def load_env_vars() -> dict[str, str]:
    return {name: os.environ[name] for name in EnvVar if name in os.environ}


def load_env() -> AppConfig:
    env_filepath = os.environ.get(EnvVar.env_file, None)
    config = {**load_env_file(env_filepath), **load_env_vars()}
    return AppConfig(**config)
