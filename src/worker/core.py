import asyncio
import logging
from asyncio import Task
from enum import StrEnum
from logging import Logger
from typing import Awaitable, Callable

from db.core import DatabaseSession
from db.models import Order
from opcuax.objects import OpcuaPrinter
from printer import ActualPrinter
from printer.models import PrinterStatus, LatestJob


class WorkerState(StrEnum):
    Unsync = "Unsync"
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


class PrinterWorker:
    def __init__(
        self,
        printer_id: int,
        session: DatabaseSession,
        actual_printer: ActualPrinter,
        opcua_printer: OpcuaPrinter,
        order_fetcher: OrderFetcher | None = None,
        interval: float = 1,
    ):
        if order_fetcher is None:
            order_fetcher = session.next_order_fifo

        self.name = f"PrinterWorker{printer_id}"
        self.logger: Logger = logging.getLogger(name=self.name)
        self.session = session
        self.actual_printer: ActualPrinter = actual_printer
        self.opcua_printer: OpcuaPrinter = opcua_printer
        self.state: WorkerState = WorkerState.Unsync
        self.current_order: Order | None = None
        self.printer_id: int = printer_id

        self._event_queue: asyncio.Queue[WorkerEvent] = asyncio.Queue()

        self.order_fetcher = order_fetcher

        self.interval = interval
        self._stop: bool = False
        self._task: Task | None = None

    async def step(self):
        stat = await self.actual_printer.current_status()
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
                raise NotImplemented

    async def run(self):
        async with self:
            while not self._stop:
                await self.step()
                await asyncio.sleep(self.interval)

    def start(self):
        self._task = asyncio.create_task(self.run())

    def stop(self):
        self._stop = True
        self._task = None

    async def handle_state(self, stat: PrinterStatus):
        match self.state:
            case WorkerState.Unsync:
                await self.when_unsync(stat)
            case WorkerState.Ready:
                await self.when_ready()
            case WorkerState.Printing:
                await self.when_printing(stat)
            case WorkerState.Printed:
                await self.when_printed()
            case WorkerState.WaitPickup:
                pass

    def pickup_finished(self):
        self._event_queue.put_nowait(WorkerEvent.Picked)

    def cancel_job(self):
        self._event_queue.put_nowait(WorkerEvent.Cancel)

    async def when_unsync(self, stat: PrinterStatus) -> None:
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
                self.logger.error("invalid order")
            case Order(), PrinterStatus(job=job):
                match job:
                    case LatestJob(file_path=order.gcode_filename(), done=True):
                        self.state = WorkerState.Printed
                    case LatestJob(file_path=order.gcode_filename(), done=False):
                        self.state = WorkerState.Printing
                    case _:
                        # order is not the latest job => must have been picked or cancelled
                        # we assume it was printed and picked
                        await self.on_picked()

    async def when_ready(self) -> None:
        order: Order = await self.order_fetcher()  # get from the queue system

        if order is None:
            self.logger.debug("no pending orders")
            return

        self.logger.info("new job for order %d", order.id)

        await self.actual_printer.upload_file(order.gcode_filename())
        await self.actual_printer.start_job(order.gcode_filename())
        await self.session.start_printing(order)

        self.current_order = order
        self.state = WorkerState.Printing

    async def when_printing(self, stat: PrinterStatus) -> None:
        job = stat.job

        self.logger.info("job progress: %f", job.progress)

        if job.done:
            await self.session.finish_printing(self.current_order)
            self.state = WorkerState.Printed

    async def when_printed(self) -> None:
        await self.actual_printer.delete_file(self.current_order.gcode_filename())
        await self.require_pickup()

        self.state = WorkerState.WaitPickup

    async def on_picked(self) -> None:
        await self.session.picked(self.current_order)
        self.session.expire(self.current_order)

        self.state = WorkerState.Unsync
        self.current_order = None

    async def on_cancelled(self) -> None:
        if self.state not in [
            WorkerState.Printing,
            WorkerState.Printed,
            WorkerState.WaitPickup,
        ]:
            self.logger.error("invalid cancellation when worker is %s", self.state)
            return

        await self.session.cancel_order(self.current_order)

        if self.state == WorkerState.Printing:
            await self.actual_printer.stop_job()
            self.state = WorkerState.Unsync  # wait until printer is ready
            self.session.expire(self.current_order)
            self.current_order = None
        else:
            self.logger.info("wait until the discarded model is picked")

    async def require_pickup(self):
        self.logger.info(
            f"simulate sending pickup request for printer {self.printer_id}"
        )

    async def _update_opcua(self, stat: PrinterStatus) -> None:
        bed, nozzle, job = stat.temp_bed, stat.temp_nozzle, stat.job

        await self.opcua_printer.current_state.set(stat.state)

        await self.opcua_printer.bed_current_temperature.set(bed.actual)
        await self.opcua_printer.bed_target_temperature.set(bed.target)
        await self.opcua_printer.nozzle_current_temperature.set(nozzle.actual)
        await self.opcua_printer.nozzle_target_temperature.set(nozzle.target)

        if job is not None:
            await self.opcua_printer.job_file.set(stat.job.file_path)
            await self.opcua_printer.job_progress.set(stat.job.progress)
            await self.opcua_printer.job_time.set(stat.job.time_used)
            await self.opcua_printer.job_time_left.set(stat.job.time_left)
            await self.opcua_printer.job_time_estimate.set(stat.job.time_approx)

    async def __aenter__(self):
        await self.session.__aenter__()
        await self.actual_printer.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
        await self.actual_printer.__aexit__(exc_type, exc_val, exc_tb)
