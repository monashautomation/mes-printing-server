import asyncio
import unittest
from datetime import datetime

from opcua.mock import MockOpcuaClient
from opcua.types import OpcuaObject, OpcuaVariable


class Foo(OpcuaObject):
    name = OpcuaVariable(name='Foo_Name', default='default')


class MockClientGetObjectTest(unittest.TestCase):
    def test_context_variables(self):
        client = MockOpcuaClient()
        obj = client.get_object(Foo, namespace_idx=3)

        self.assertEqual(obj.__client__, client)
        self.assertEqual(obj.__ns__, 3)


class MockClientQueryTest(unittest.IsolatedAsyncioTestCase):

    async def test_get_default(self):
        client = MockOpcuaClient()
        namespace = 'ns=3;s=Foo_Name'
        value = await client.get(namespace, default='default')

        self.assertEqual(value, 'default')
        self.assertEqual(client.table[namespace], 'default')

    async def test_get(self):
        client = MockOpcuaClient()
        namespace = 'ns=3;s=Foo_Name'
        client.table[namespace] = 'foobar'

        value = await client.get(namespace)

        self.assertEqual(value, 'foobar')

    async def test_set(self):
        client = MockOpcuaClient()
        namespace = 'ns=3;s=Foo_Name'

        await client.set(namespace, 'foobar')

        self.assertEqual(client.table[namespace], 'foobar')


class MockOpcuaObjectTest(unittest.IsolatedAsyncioTestCase):

    async def test_get_default(self):
        client = MockOpcuaClient()
        obj = client.get_object(Foo, namespace_idx=3)

        value = await obj.name.get()

        self.assertEqual(value, 'default')
        self.assertEqual(client.table['ns=3;s=Foo_Name'], 'default')

    async def test_get(self):
        client = MockOpcuaClient()
        obj = client.get_object(Foo, namespace_idx=3)

        client.table['ns=3;s=Foo_Name'] = 'foobar'

        value = await obj.name.get()

        self.assertEqual(value, 'foobar')

    async def test_set(self):
        client = MockOpcuaClient()
        obj = client.get_object(Foo, namespace_idx=3)

        client.table['ns=3;s=Foo_Name'] = 'foobar'

        value = await obj.name.get()

        self.assertEqual(value, 'foobar')


class MultipleMockOpcuaObjectTest(unittest.IsolatedAsyncioTestCase):

    async def test_mutation(self):
        client = MockOpcuaClient()
        foo1 = client.get_object(Foo, namespace_idx=1)
        foo2 = client.get_object(Foo, namespace_idx=2)

        await foo1.name.set('foo1')
        await foo2.name.set('foo2')

        name1 = await foo1.name.get()
        name2 = await foo2.name.get()

        self.assertEqual(name1, 'foo1')
        self.assertEqual(name2, 'foo2')

    async def test_concurrent_set(self):
        client = MockOpcuaClient(delay=0.25)
        foo1 = client.get_object(Foo, namespace_idx=1)
        foo2 = client.get_object(Foo, namespace_idx=2)

        start_time = datetime.now()

        async def update_name(foo: Foo, name: str):
            await foo.name.set(name)  # 0.25s
            return await foo.name.get()  # 0.25s

        async with asyncio.TaskGroup() as group:
            task1 = group.create_task(update_name(foo1, 'foo1'))
            task2 = group.create_task(update_name(foo2, 'foo2'))

        sec_used = (datetime.now() - start_time).total_seconds()

        self.assertEqual(task1.result(), 'foo1')
        self.assertEqual(task2.result(), 'foo2')
        self.assertLess(sec_used, 0.6)


if __name__ == '__main__':
    unittest.main()
