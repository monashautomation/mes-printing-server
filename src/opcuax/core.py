from types import TracebackType
from typing import Any, Generic, Optional, TypeVar

from asyncua import Client, Node, ua


class OpcuaNode:
    ua_node: Node

    def __init__(self, name: str):
        self.ua_name = name

    def clone(self) -> "OpcuaNode":
        return type(self)(name=self.ua_name)

    @property
    def node_id(self) -> str:
        return str(self.ua_node.nodeid)


T = TypeVar("T")


class OpcuaVariable(OpcuaNode, Generic[T]):
    def __init__(self, name: str, cls: type[T], default: T):
        super().__init__(name)
        self.cls: type[T] = cls
        self.default: T = default

    async def get(self) -> T:
        value = await self.ua_node.get_value()
        assert isinstance(value, self.cls)
        return value

    async def set(self, value: T | None) -> None:
        value = value or self.default
        data_type = await self.ua_node.read_data_type_as_variant_type()
        await self.ua_node.write_value(ua.DataValue(ua.Variant(value, data_type)))

    def clone(self) -> OpcuaNode:
        return type(self)(name=self.ua_name, cls=self.cls, default=self.default)


# IDE doesn't provide auto complete if using functools.partial
class _OpcuaVar:
    def __init__(self, cls: type[T], default: T):
        self.cls = cls
        self.default = default

    def __call__(self, name: str, default: T | None = None) -> OpcuaVariable[T]:
        return OpcuaVariable(name=name, cls=self.cls, default=default or self.default)


OpcuaStrVar = _OpcuaVar(cls=str, default="")
OpcuaIntVar = _OpcuaVar(cls=int, default=0)
OpcuaFloatVar = _OpcuaVar(cls=float, default=0.0)
OpcuaBoolVar = _OpcuaVar(cls=bool, default=False)


class OpcuaObject(OpcuaNode):
    async def __to_dict(
        self,
        data: dict[str, Any],
        parent_name: str | None = None,
        flatten: bool = False,
    ) -> dict[str, Any]:
        for name, attr in self.__dict__.items():
            key = name
            if flatten and parent_name is not None:
                key = f"{parent_name}_{name}"
            match attr:
                case OpcuaVariable() as var:
                    data[key] = await var.get()
                case OpcuaObject() as obj:
                    if flatten:
                        await obj.__to_dict(data=data, parent_name=key, flatten=True)
                    else:
                        data[key] = await obj.__to_dict(
                            data={}, parent_name=key, flatten=False
                        )

        return data

    async def to_dict(self, flatten: bool = False) -> dict[str, Any]:
        return await self.__to_dict(data={}, flatten=flatten)


_OpcuaObject = TypeVar("_OpcuaObject", bound=OpcuaObject)


class OpcuaClient:
    def __init__(self, url: str):
        self.client: Client = Client(url)

    async def set_ua_node(self, parent: Node, node: OpcuaNode) -> None:
        node.ua_node = await parent.get_child(node.ua_name)

        if not isinstance(node, OpcuaObject):
            return

        for name, attr in type(node).__dict__.items():
            if not isinstance(attr, OpcuaNode):
                continue
            child = attr.clone()
            setattr(node, name, child)
            await self.set_ua_node(node.ua_node, child)

    async def get_object(self, cls: type[_OpcuaObject], name: str) -> _OpcuaObject:
        obj = cls(name)
        await self.set_ua_node(self.client.get_objects_node(), obj)
        return obj

    async def __aenter__(self) -> "OpcuaClient":
        await self.client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
