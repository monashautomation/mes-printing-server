from typing import TypeVar, Optional, Type, Generic

from asyncua import Client as AsyncuaClient, ua

OpcuaValue = TypeVar("OpcuaValue", int, str, float, bool)
_OpcuaClient = TypeVar("_OpcuaClient", bound="BaseOpcuaClient")
OpcuaObjectNode = TypeVar("OpcuaObjectNode", bound="OpcuaObject")


class OpcuaClient(AsyncuaClient):
    def __init__(self, url: str):
        super().__init__(url)
        self.url = url

    async def get(
        self, node_id: str, default: Optional[OpcuaValue] = None
    ) -> OpcuaValue:
        node = self.get_node(node_id)
        return await node.read_value()

    async def set(self, node_id: str, value: OpcuaValue) -> None:
        node = self.get_node(node_id)
        data_type = await node.read_data_type_as_variant_type()
        await node.write_value(ua.DataValue(ua.Variant(value, data_type)))

    def get_object(self, obj_type: Type[OpcuaObjectNode], ns: int) -> OpcuaObjectNode:
        return obj_type(client=self, ns=ns)


class OpcuaObject:
    def __new__(cls, client: _OpcuaClient, ns: int, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        obj.__client__ = client
        obj.__ns__ = ns

        for name, cls_attr in cls.__dict__.items():
            if isinstance(cls_attr, OpcuaVariable):
                mutator = AsyncMutator(
                    name=cls_attr.name, default=cls_attr.default, client=client, ns=ns
                )
                setattr(obj, name, mutator)

        return obj

    def namespace(self) -> int:
        return self.__ns__

    def client(self) -> _OpcuaClient:
        return self.__client__


class OpcuaVariable(Generic[OpcuaValue]):
    def __init__(self, name: str, default: Optional[OpcuaValue] = None):
        self.name: str = name
        self.default: Optional[OpcuaValue] = default


class AsyncMutator(Generic[OpcuaValue]):
    def __init__(
        self,
        name: str,
        client: OpcuaClient,
        ns: int,
        default: Optional[OpcuaValue] = None,
    ):
        self.client: OpcuaClient = client
        self.node_id: str = f"ns={ns};s={name}"
        self.default: Optional[OpcuaValue] = default

    async def get(self) -> OpcuaValue:
        return await self.client.get(self.node_id, self.default)

    async def set(self, value: OpcuaValue) -> None:
        await self.client.set(self.node_id, value)
