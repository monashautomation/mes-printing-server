import asyncio
import logging
from asyncio import Queue, Task
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import StrEnum
from logging import Logger
from types import TracebackType
from typing import NamedTuple

from aiohttp import ClientConnectorError
from mes_opcua_server.models import Printer as OpcuaPrinter
from opcuax import OpcuaClient
from pydantic import HttpUrl

from db import DatabaseSession, Printer
from db.models import Order
from printer import ActualPrinter, PrusaPrinter
from printer.models import LatestJob, PrinterStatus


class Scheduler:
    def __init__(self, session: DatabaseSession, auto_assign: bool = False):
        self.ready_workers: Queue[PrinterWorker] = Queue()
        self._task: Task[None] | None = None
        self.session: DatabaseSession = session
        self.auto_assign: bool = auto_assign

    def run(self):
        self._task = asyncio.create_task(self.loop())

    def stop(self):
        if self._task:
            self._task.cancel()

    async def loop(self):
        while True:
            worker = await self.ready_workers.get()
            if self.auto_assign:
                orders = await self.session.pending_order_ids()
            else:
                orders = await self.session.assigned_pending_order_ids(
                    worker.printer_id
                )

            if len(orders) == 0:
                continue

            order_id = orders[0]
            worker.pending_orders.put_nowait(order_id)


class WorkerState(StrEnum):
    Unknown = "Unknown"
    Ready = "ready"
    Printing = "printing"
    Paused = "paused"
    Stopped = "stopped"
    Error = "error"
    Printed = "Printed"
    WaitPickup = "WaitPickup"


class WorkerEvent(StrEnum):
    Cancel = "Cancel"
    Picked = "Picked"


OrderFetcher = Callable[[], Awaitable[Order | None]]


class _Printer(NamedTuple):
    actual: ActualPrinter
    opcua: OpcuaPrinter
    model: Printer
    opcua_name: str


class PrinterState(PrinterStatus):
    name: str
    model: str
    camera_url: str


class PrinterWorker:
    def __init__(
        self,
        printer_id: int,
        opcua_name: str,
        session: DatabaseSession,
        actual_printer: ActualPrinter,
        opcua_printer: OpcuaPrinter,
        model: Printer,
        opcua_client: OpcuaClient,
        scheduler: Scheduler,
        interval: float = 1,
    ) -> None:
        self.session = session
        self.printer: _Printer = _Printer(
            actual=actual_printer,
            opcua=opcua_printer,
            model=model,
            opcua_name=opcua_name,
        )
        self.state: WorkerState = WorkerState.Unknown
        self.current_order: Order | None = None
        self.printer_id: int = printer_id
        self.opcua_client: OpcuaClient = opcua_client

        self.name = f"Worker-{self.printer.opcua_name}"
        self.logger: Logger = logging.getLogger(name=self.name)

        self._event_queue: asyncio.Queue[WorkerEvent] = asyncio.Queue()

        self.pending_orders: asyncio.Queue[int] = asyncio.Queue[int]()
        self.scheduler: Scheduler = scheduler

        self.interval = interval
        self._stop: bool = False
        self._task: Task[None] | None = None
        self._latest_state: PrinterState | None = None

    async def step(self) -> None:
        stat = await self.printer.actual.current_status()
        await self._update_opcua(stat)

        if self._event_queue.empty():
            await self.handle_state(stat)
            return

        event = self._event_queue.get_nowait()

        match event:
            case WorkerEvent.Picked:
                await self.on_picked()
            case WorkerEvent.Cancel:
                await self.on_cancelled()
            case _:
                raise NotImplementedError

    async def run(self) -> None:
        async with self:
            while not self._stop:
                try:
                    await self.step()
                except ClientConnectorError:
                    self.state = WorkerState.Unknown
                except Exception as e:
                    self.logger.exception(e)
                await asyncio.sleep(self.interval)
            self.logger.warning("printer worker stops for printer %d", self.printer_id)

    def start(self) -> None:
        self.logger.warning("printer worker starts for printer %d", self.printer_id)
        self._stop = False
        self._task = asyncio.create_task(self.run())

    def stop(self) -> None:
        self._stop = True
        self._task = None

    async def latest_state(self) -> PrinterState:
        while self._latest_state is None:
            await asyncio.sleep(self.interval)
        assert self._latest_state is not None
        return self._latest_state

    async def handle_state(self, stat: PrinterStatus) -> None:
        self.logger.info(stat.model_dump())
        match self.state:
            case WorkerState.Unknown:
                await self.when_unknown(stat)
            case WorkerState.Ready:
                await self.when_ready()
            case WorkerState.Printing:
                await self.when_printing(stat)
            case WorkerState.Printed:
                await self.when_printed()
            case WorkerState.WaitPickup:
                pass

    def pickup_finished(self) -> None:
        self._event_queue.put_nowait(WorkerEvent.Picked)

    def cancel_job(self) -> None:
        self._event_queue.put_nowait(WorkerEvent.Cancel)

    async def when_unknown(self, stat: PrinterStatus) -> None:
        order = await self.session.current_order(self.printer_id)
        self.current_order = order

        match order, stat:
            case None, PrinterStatus(is_ready=True):
                self.state = WorkerState.Ready
            case None, _:
                self.logger.warning("printer is busy with an external job")
            case _, PrinterStatus(is_error=True):
                self.logger.error("printer is in error state")
            case Order(), PrinterStatus(job=None):
                # could happen if printer storage is changed
                # or server is restarted with mock printers
                await self.on_picked()
            case Order() as order, PrinterStatus(job=job):
                match job:
                    case LatestJob(file_path=path) if path == order.gcode_filename():
                        if job.done:
                            self.state = WorkerState.Printed
                        else:
                            self.state = WorkerState.Printing
                            if order.cancelled:
                                self.cancel_job()
                    case _:
                        # order is not the latest job => must have been picked or cancelled
                        # we assume it was printed and picked
                        await self.on_picked()

    async def when_ready(self) -> None:
        self.scheduler.ready_workers.put_nowait(self)

        if self.pending_orders.empty():
            self.logger.debug("no pending orders")
            return

        order_id = self.pending_orders.get_nowait()
        order: Order | None = await self.session.get(Order, order_id)

        if not order:
            return

        self.logger.info("new job for order %d", order.id)

        order.printer_id = self.printer_id
        await self.session.upsert(order)

        await self.printer.actual.upload_file(order.gcode_file_path)
        await self.printer.actual.start_job(order.gcode_file_path)
        await self.session.start_printing(order)

        self.current_order = order
        self.state = WorkerState.Printing

    async def when_printing(self, stat: PrinterStatus) -> None:
        job = stat.job

        if job is None or job.done:
            self.state = WorkerState.Printed

    async def when_printed(self) -> None:
        assert self.current_order is not None

        await self.session.finish_printing(self.current_order)
        await self.printer.actual.delete_file(self.current_order.gcode_filename())
        await self.require_pickup()

        self.state = WorkerState.WaitPickup

    async def on_picked(self) -> None:
        assert self.current_order is not None

        await self.session.picked(self.current_order)
        self.session.expire(self.current_order)

        self.state = WorkerState.Unknown
        self.current_order = None

    async def on_cancelled(self) -> None:
        if self.state not in [
            WorkerState.Printing,
            WorkerState.Printed,
            WorkerState.WaitPickup,
        ]:
            self.logger.error("invalid cancellation when worker is %s", self.state)
            return

        if self.state == WorkerState.Printing:
            await self.printer.actual.stop_job()
            self.state = WorkerState.Printed
        else:
            self.logger.info("wait until the discarded model is picked")

    async def require_pickup(self) -> None:
        self.logger.warning(
            f"simulate sending pickup request for printer {self.printer_id}"
        )

    async def _update_opcua(self, stat: PrinterStatus) -> None:
        model = self.printer.model.model or str(self.printer.model.api)
        camera_url = self.printer.model.camera_url or "http://localhost"
        bed, nozzle, job = stat.temp_bed, stat.temp_nozzle, stat.job

        self._latest_state = PrinterState(
            name=self.printer.opcua_name,
            state=stat.state,
            model=model,
            camera_url=camera_url,
            temp_bed=bed,
            temp_nozzle=nozzle,
            job=job,
        )

        self.printer.opcua.url = HttpUrl(self.printer.actual.url)
        self.printer.opcua.update_time = datetime.now()
        self.printer.opcua.state = stat.state
        self.printer.opcua.bed.target = bed.target
        self.printer.opcua.bed.actual = bed.actual
        self.printer.opcua.nozzle.target = nozzle.target
        self.printer.opcua.nozzle.actual = nozzle.actual
        self.printer.opcua.camera_url = HttpUrl(camera_url)
        self.printer.opcua.model = model

        if job is not None:
            self.printer.opcua.job.file = job.file_path
            self.printer.opcua.job.progress = job.progress or 0
            self.printer.opcua.job.time_used = job.time_used or 0
            self.printer.opcua.job.time_left = job.time_left or 0
            self.printer.opcua.job.time_left_approx = job.time_approx or 0

        await self.opcua_client.commit()

    async def previewed_model(self) -> bytes | None:
        if (
            not isinstance(self.printer.actual, PrusaPrinter)
            or not self._latest_state
            or not self._latest_state.job.previewed_model_url
        ):
            return None

        return await self.printer.actual.previewed_model(
            self._latest_state.job.previewed_model_url
        )

    async def __aenter__(self) -> "PrinterWorker":
        await self.session.__aenter__()
        await self.printer.actual.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
        await self.printer.actual.__aexit__(exc_type, exc_val, exc_tb)
