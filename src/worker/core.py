import asyncio
import logging
from enum import StrEnum
from logging import Logger
from typing import Awaitable, Callable, Union, Optional

import mes
from db.core import DatabaseSession
from db.models import Order
from octo import OctoprintClient
from opcuax.objects import OpcuaPrinter
from worker.opcua import OpcuaPrinterUpdator


class WorkerState(StrEnum):
    Ready = "Ready"  # printer is ready to print
    Connecting = "Connecting"  # connecting to printer
    Connected = "Connected"  # printer is connected, but is not ready
    Heating = "Heating"  # printer is heating, **printer state** is still "ready"
    Printing = "Printing"  # printer is printing
    Printed = "Printed"  # printing is finished
    WaitingForPickup = "WaitingForPickup"  # wait until the printed model is picked up
    Picked = "Picked"  # the printed model is picked
    Error = "Error"  # printer state is error


PrinterState = Union[WorkerState.Ready, WorkerState.Printing, WorkerState.Error]


class WorkerEvent(StrEnum):
    Cancel = "Cancel"
    Pick = "Pick"


StateHandler = Callable[["PrinterWorker"], Awaitable[None]]
EventHandler = Callable[["PrinterWorker"], Awaitable[None]]

OrderFetcher = Callable[[], Awaitable[Optional[Order]]]
PickupNotifier = Callable[[str], Awaitable[None]]


class PrinterWorker:
    state_handlers: dict[WorkerState, StateHandler] = {}
    event_handlers: dict[WorkerEvent, EventHandler] = {}

    def __init__(
        self,
        session: DatabaseSession,
        octo: OctoprintClient,
        opcua_printer: OpcuaPrinter,
        order_fetcher: OrderFetcher = mes.next_printing_order,
        pickup_notifier: PickupNotifier = mes.notify_pickup,
    ):
        self.logger: Logger = logging.getLogger(f"PrinterWorker - {octo.host}")
        self.session = session
        self.octo = octo
        self.opcua_printer = opcua_printer
        self.opcua_printer_updator = OpcuaPrinterUpdator(opcua_printer)
        self.state: WorkerState = WorkerState.Connecting
        self.current_order: Order | None = None

        self._event_queue: asyncio.Queue = asyncio.Queue()

        self.order_fetcher = order_fetcher
        self.pickup_notifier = pickup_notifier

    async def run(self):
        while True:
            await self.work()
            await asyncio.sleep(1)

    async def work(self):
        if not self._event_queue.empty():
            event = self._event_queue.get_nowait()
            await self.handle_event(event)
        else:
            await self.handle_state()

    async def handle_state(self):
        handler = PrinterWorker.state_handlers[self.state]
        await handler(self)

    async def handle_event(self, event: WorkerEvent):
        handler = PrinterWorker.event_handlers[event]
        await handler(self)

    @staticmethod
    def state_handler(state: WorkerState) -> Callable[[StateHandler], StateHandler]:
        def register_handler(handler: StateHandler) -> StateHandler:
            PrinterWorker.state_handlers[state] = handler
            return handler

        return register_handler

    @staticmethod
    def event_handler(event: WorkerEvent) -> Callable[[EventHandler], EventHandler]:
        def register_handler(handler: EventHandler) -> EventHandler:
            PrinterWorker.event_handlers[event] = handler
            return handler

        return register_handler

    def put_event(self, event: WorkerEvent):
        self._event_queue.put_nowait(event)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
