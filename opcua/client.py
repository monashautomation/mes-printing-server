from asyncua import Client, ua

from opcua.types import BaseOpcuaClient, OpcuaValue


class OpcuaClient(BaseOpcuaClient):
    def __init__(self, url: str):
        self.client = Client(url=url)

    def __aenter__(self):
        self.client.connect()

    def __aexit__(self, exc_type, exc_val, exc_tb):
        self.client.disconnect()

    async def connect(self) -> None:
        await self.client.connect()

    async def disconnect(self) -> None:
        await self.client.disconnect()

    async def get(self, node_id: str, default=None) -> OpcuaValue:
        node = self.client.get_node(node_id)
        return await node.read_value()

    async def set(self, node_id: str, value: OpcuaValue) -> None:
        node = self.client.get_node(node_id)
        data_type = await node.read_data_type_as_variant_type()
        await node.write_value(ua.DataValue(ua.Variant(value, data_type)))
