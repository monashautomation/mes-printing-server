from abc import ABC, abstractmethod
from typing import TypeVar, Optional, Type, Generic

OpcuaValue = TypeVar('OpcuaValue', int, str, float, bool)


class OpcuaObject:
    __client__: 'BaseOpcuaClient'
    __ns__: int


class BaseOpcuaClient(ABC):

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def get(self, node_id: str, default: Optional[OpcuaValue] = None) -> OpcuaValue:
        pass

    @abstractmethod
    async def set(self, node_id: str, value: OpcuaValue) -> None:
        pass

    ObjectNode = TypeVar('ObjectNode', bound=OpcuaObject)

    def get_object(self, obj_type: Type[ObjectNode], namespace_idx: int) -> ObjectNode:
        obj = obj_type()
        obj.__client__ = self
        obj.__ns__ = namespace_idx
        return obj


class AsyncMutator(Generic[OpcuaValue]):

    def __init__(self, name: str, storage: BaseOpcuaClient, ns: int, default: Optional[OpcuaValue] = None):
        self.storage: BaseOpcuaClient = storage
        self.node_id: str = f'ns={ns};s={name}'
        self.default: Optional[OpcuaValue] = default

    async def get(self) -> OpcuaValue:
        return await self.storage.get(self.node_id, self.default)

    async def set(self, value: OpcuaValue) -> None:
        await self.storage.set(self.node_id, value)


class OpcuaVariable(Generic[OpcuaValue]):

    def __init__(self, name: str, default: Optional[OpcuaValue] = None):
        self.name: str = name
        self.default: Optional[OpcuaValue] = default

    def __get__(self, instance: OpcuaObject, owner) -> AsyncMutator:
        return AsyncMutator(name=self.name, storage=instance.__client__, ns=instance.__ns__, default=self.default)
