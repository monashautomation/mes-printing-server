import asyncio
from types import TracebackType
from typing import Any

from .core import OpcuaClient, OpcuaNode, OpcuaObject, OpcuaVariable, T, _OpcuaObject


class MockOpcuaVariable(OpcuaVariable[T]):
    def __init__(self, name: str, cls: type[T], default: T):
        super().__init__(name=name, cls=cls, default=default)
        self.value = self.default

    async def get(self) -> T:
        return self.value

    async def set(self, value: T | None) -> None:
        self.value = value or self.default


class MockOpcuaClient(OpcuaClient):
    def __init__(self, delay: float = 0.1, url: str = "mock"):
        super().__init__(url)
        self.table: dict[str, Any] = {}
        self.delay: float = delay

    async def connect(self) -> None:
        await asyncio.sleep(self.delay)

    async def disconnect(self) -> None:
        await asyncio.sleep(self.delay)

    def init_var(self, node: OpcuaNode) -> None:
        for name, attr in type(node).__dict__.items():
            match attr:
                case OpcuaVariable(cls=cls, default=default):
                    var = MockOpcuaVariable(name=name, cls=cls, default=default)
                    setattr(node, name, var)
                case OpcuaObject():
                    obj = type(attr)(name=name)
                    setattr(node, name, obj)
                    self.init_var(obj)

    async def get_object(self, cls: type[_OpcuaObject], name: str) -> _OpcuaObject:
        obj = cls(name)
        self.init_var(obj)
        return obj

    async def __aenter__(self) -> "OpcuaClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return
