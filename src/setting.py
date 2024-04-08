from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import (
    AnyUrl,
    DirectoryPath,
    NewPath,
    PositiveFloat,
    PositiveInt,
    UrlConstraints,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

OpcuaUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["opc.tcp"])]


class LoggingLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    ERROR = "ERROR"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AppSettings(BaseSettings):
    database_url: AnyUrl = AnyUrl("sqlite+aiosqlite://")
    opcua_server_url: OpcuaUrl = OpcuaUrl("opc.tcp://mock-server:4840")
    opcua_server_namespace: str = "http://monashautomation.com/opcua-server"
    upload_path: NewPath | DirectoryPath = Path("./upload")
    printer_worker_interval: PositiveFloat = 5
    order_fetcher_interval: PositiveFloat = 5
    auto_schedule: bool = True
    mock_printer_interval: PositiveFloat = 2
    mock_printer_job_time: PositiveInt = 30
    mock_printer_target_bed_temperature: PositiveInt = 100
    mock_printer_target_bed_nozzle: PositiveInt = 120
    logging_level: LoggingLevel = LoggingLevel.INFO


class EnvAppSettings(AppSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


app_settings: AppSettings = EnvAppSettings()


def display() -> None:
    s = EnvAppSettings()
    s.upload_path.mkdir(exist_ok=True)
    print(s.model_dump_json(indent=4))
