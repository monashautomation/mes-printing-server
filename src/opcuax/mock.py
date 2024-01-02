import asyncio

from opcuax.client import BaseOpcuaClient
from opcuax.core import OpcuaValue


class MockOpcuaClient(BaseOpcuaClient):
    def __init__(self, delay: float = 0.1):
        self.table = {}
        self.delay: float = delay

    async def connect(self) -> None:
        await asyncio.sleep(self.delay)

    async def disconnect(self) -> None:
        await asyncio.sleep(self.delay)

    async def get(self, node_id: str, default=None) -> OpcuaValue:
        await asyncio.sleep(self.delay)
        return self.table.setdefault(node_id, default)

    async def set(self, node_id: str, value: OpcuaValue) -> None:
        await asyncio.sleep(self.delay)
        self.table[node_id] = value
