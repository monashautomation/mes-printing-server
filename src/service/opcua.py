from typing import Self

from mes_opcua_server.models import Printer as OpcuaPrinter
from opcuax import OpcuaClient
from opcuax.model import TBaseModel, TOpcuaModel

from setting import app_settings


class MockOpcuaClient(OpcuaClient):
    async def refresh(self, model: TBaseModel) -> None:
        return

    async def update(self, name: str, model: TOpcuaModel) -> TOpcuaModel:
        return model

    async def commit(self) -> None:
        while not self.update_tasks.empty():
            self.update_tasks.get_nowait()

    async def get_object(
        self, model_class: type[TOpcuaModel], name: str
    ) -> TOpcuaModel:
        return model_class()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return


class OpcuaService:
    def __init__(self):
        self._client: OpcuaClient = self.create_opcua_client()
        self._connected: bool = False

    @staticmethod
    def create_opcua_client() -> OpcuaClient:
        url = str(app_settings.opcua_server_url)
        ns = app_settings.opcua_server_namespace

        if "mock" in url:
            return MockOpcuaClient(endpoint=url, namespace=ns)
        else:
            return OpcuaClient(endpoint=url, namespace=ns)

    async def connect(self) -> None:
        await self._client.__aenter__()
        self._connected = True

    async def get_printer(self, name: str) -> OpcuaPrinter:
        if not self._connected:
            raise RuntimeError("OpcuaService should be connected before use")
        return await self._client.get_object(OpcuaPrinter, name)

    async def commit(self) -> None:
        if not self._connected:
            raise RuntimeError("OpcuaService should be connected before use")
        await self._client.commit()

    async def close(self):
        await self._client.__aexit__(None, None, None)
        self._connected = False


opcua_service: OpcuaService = OpcuaService()
