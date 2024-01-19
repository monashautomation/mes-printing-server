import asyncio
import logging
from asyncio import Task
from enum import StrEnum
from logging import Logger
from typing import Awaitable, Callable, Optional

import mes
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
    Picked = "Picked"


class WorkerEvent(StrEnum):
    Cancel = "Cancel"
    Picked = "Picked"
    Stop = "Stop"


OrderFetcher = Callable[[], Awaitable[Optional[Order]]]
PickupNotifier = Callable[[str], Awaitable[None]]


class PrinterWorker:
    def __init__(
        self,
        session: DatabaseSession,
        actual_printer: ActualPrinter,
        opcua_printer: OpcuaPrinter,
        printer_id: int,
        order_fetcher: OrderFetcher = mes.next_printing_order,
        pickup_notifier: PickupNotifier = mes.notify_pickup,
        interval: int = 1,
    ):
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
        self.pickup_notifier = pickup_notifier

        self.interval = interval
        self.task: Task | None = None

    def start(self):
        self.task = asyncio.create_task(self._run_loop(), name=self.name)

    async def _run_loop(self):
        while True:
            await self.step()
            await asyncio.sleep(self.interval)

    async def _stop_loop(self):
        self.task.cancel()
        self.task = None
        await self.session.close()

    async def step(self):
        stat = await self.actual_printer.current_status()
        await self._update_opcua(stat)

        if not self._event_queue.empty():
            event = self._event_queue.get_nowait()
            match event:
                case WorkerEvent.Picked:
                    self.state = WorkerState.Picked
                case WorkerEvent.Cancel:
                    await self.on_cancelled()
                case WorkerEvent.Stop:
                    await self._stop_loop()
        else:
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
                case WorkerState.Picked:
                    await self.when_picked()

    def _send(self, event: WorkerEvent):
        self._event_queue.put_nowait(event)

    def pickup_finished(self):
        self._event_queue.put_nowait(WorkerEvent.Picked)

    def cancel_job(self):
        self._event_queue.put_nowait(WorkerEvent.Cancel)

    def stop(self):
        self._event_queue.put_nowait(WorkerEvent.Stop)

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
                        self.state = WorkerState.Picked

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
        await self.actual_printer.delete_file(self.current_order.gcode_file_path)
        await self.pickup_notifier(self.actual_printer.url)

        self.state = WorkerState.WaitPickup

    async def when_picked(self) -> None:
        await self.session.picked(self.current_order)
        self.session.expire(self.current_order)

        self.state = WorkerState.Ready
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
