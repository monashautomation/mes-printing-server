from typing import Annotated

from pydantic import AnyUrl, NewPath, DirectoryPath, UrlConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

OpcuaUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["opc.tcp"])]


class AppSettings(BaseSettings):
    database_url: AnyUrl
    opcua_server_url: AnyUrl
    upload_path: NewPath | DirectoryPath


class EnvAppSettings(AppSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def display():
    s = EnvAppSettings()
    s.upload_path.mkdir(exist_ok=True)
    print(s.model_dump_json(indent=4))
