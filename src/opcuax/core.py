from typing import Generic, Optional, Type, TypeVar

from asyncua import Client as AsyncuaClient
from asyncua import ua

OpcuaValue = TypeVar("OpcuaValue", int, str, float, bool)
_OpcuaClient = TypeVar("_OpcuaClient", bound="OpcuaClient")
OpcuaObjectNode = TypeVar("OpcuaObjectNode", bound="OpcuaObject")


class OpcuaClient(AsyncuaClient):
    def __init__(self, url: str):
        super().__init__(url)
        self.url = url

    async def get(self, node_id: str, default: OpcuaValue | None = None) -> OpcuaValue:
        node = self.get_node(node_id)
        return await node.read_value()

    async def set(self, node_id: str, value: OpcuaValue) -> None:
        node = self.get_node(node_id)
        data_type = await node.read_data_type_as_variant_type()
        await node.write_value(ua.DataValue(ua.Variant(value, data_type)))

    def get_object(self, obj_type: type[OpcuaObjectNode], ns: int) -> OpcuaObjectNode:
        return obj_type(client=self, ns=ns)


class OpcuaVariable(Generic[OpcuaValue]):
    __opcua_object__: "OpcuaObject"

    def __init__(self, name: str, default: OpcuaValue | None = None):
        self.name: str = name
        self.default: OpcuaValue | None = default

    async def get(self) -> OpcuaValue:
        return await self.__opcua_object__.get(self)

    async def set(self, value: OpcuaValue) -> None:
        await self.__opcua_object__.set(self, value)


class OpcuaObject:
    def __new__(cls, client: _OpcuaClient, ns: int, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        obj.__client__ = client
        obj.__ns__ = ns

        for name, cls_attr in cls.__dict__.items():
            match cls_attr:
                case OpcuaVariable(name=var_name, default=var_default):
                    var = OpcuaVariable(name=var_name, default=var_default)
                    var.__opcua_object__ = obj
                    setattr(obj, name, var)
        return obj

    def namespace(self) -> int:
        return self.__ns__

    def client(self) -> _OpcuaClient:
        return self.__client__

    def node_id(self, var: OpcuaVariable) -> str:
        return f"ns={self.__ns__};s={var.name}"

    async def get(self, var: OpcuaVariable) -> OpcuaValue:
        return await self.__client__.get(self.node_id(var), var.default)

    async def set(self, var: OpcuaVariable, value: OpcuaValue) -> None:
        await self.__client__.set(self.node_id(var), value)
