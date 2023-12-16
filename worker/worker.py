import asyncio
import logging
import math
from datetime import datetime
from enum import StrEnum, Enum, auto
from logging import Logger
from typing import Callable, Awaitable

from sqlalchemy.orm import selectinload
from sqlmodel import select

import mes
from db import DatabaseSession
from models import Order, Job, OrderStatus
from octo.client import OctoClient, PrinterStateError
from octo.models import PrinterStateFlags, TemperatureData, CurrentJob
from opcua.objects import OpcuaPrinter

_EventHandler = Callable[[], Awaitable[None]]


class JobState(StrEnum):
    Connecting = "Connecting"  # connecting to printer
    Connected = "Connected"  # printer is connected, but is not ready
    Ready = "Ready"  # printer is ready to print
    Heating = "Heating"  # printer is heating, **printer state** is still "ready"
    Printing = "Printing"  # printer is printing
    Printed = "Printed"  # printing is finished
    WaitingForPickup = "WaitingForPickup"  # wait until the printed model is picked up
    Picked = "Picked"  # the printed model is picked
    Error = "Error"  # printer state is error


class JobEvent(Enum):
    Cancel = auto()


def _is_heating_complete(temp: TemperatureData) -> bool:
    return math.fabs(temp.target - temp.actual) <= 2


def _parse_job_state(printer_state_flags: PrinterStateFlags) -> JobState:
    if printer_state_flags.ready:
        return JobState.Ready
    elif printer_state_flags.printing:
        return JobState.Printing
    elif printer_state_flags.error:
        return JobState.Error
    else:
        raise ValueError("cannot parse printer state flags to job state")


class JobWorker:
    def __init__(
        self, session: DatabaseSession, octo: OctoClient, opcua_printer: OpcuaPrinter
    ):
        super().__init__()
        self.logger: Logger = logging.getLogger(f"PrinterJobWorker - {octo.host}")
        self.session: DatabaseSession = session
        self.octo: OctoClient = octo
        self.opcua_printer: OpcuaPrinter = opcua_printer
        self.state: JobState = JobState.Connecting
        self.current_job: Job | None = None

        self.event_queue: asyncio.Queue = asyncio.Queue()

    async def loop(self, interval: int = 1) -> None:
        while True:
            await self.work()
            await asyncio.sleep(interval)

    async def work(self) -> None:
        if not self.event_queue.empty():
            event = self.event_queue.get_nowait()
            assert event is JobEvent.Cancel
            await self.on_cancel()
        else:
            match self.state:
                case JobState.Connecting:
                    await self.when_connecting()
                case JobState.Connected:
                    await self.when_connected()
                case JobState.Ready:
                    await self.when_ready()
                case JobState.Heating:
                    await self.when_heating()
                case JobState.Printing:
                    await self.when_printing()
                case JobState.Printed:
                    await self.when_printed()
                case JobState.WaitingForPickup:
                    await self.when_waiting_for_pickup()
                case JobState.Picked:
                    await self.when_picked()
                case JobState.Error:
                    await self.when_error()

    async def when_connecting(self) -> None:
        try:
            await self.octo.connect()
            self.state = JobState.Connected
        except ValueError:
            logging.error("connect param is invalid")

    async def when_connected(self) -> None:
        try:
            printer_status = await self.octo.current_printer_status()
            self.state = _parse_job_state(printer_status.state.flags)

            if self.state is JobState.Printing:
                self.current_job = await self._get_current_printing_job()

        except PrinterStateError:
            self.logger.error("Printer is not operational")

    async def when_ready(self) -> None:
        order: Order = await mes.next_printing_order()  # get from the queue system

        self.current_job = await self._create_job(order)

        self.state = JobState.Heating

    async def when_heating(self) -> None:
        temp_data = await self.octo.current_temperature()
        bed = temp_data.bed
        nozzle = temp_data.tool0

        await self._update_opcua_printer_temp(bed=bed, nozzle=nozzle)

        if _is_heating_complete(bed) and _is_heating_complete(nozzle):
            file_path = self.current_job.order.gcode_file_path
            await self.octo.upload_file_to_print(file_path)
            self.state = JobState.Printing

    async def when_printing(self) -> None:
        job_status: CurrentJob = await self.octo.current_job()

        await self._update_opcua_printer_job(job_status)

        if job_status.progress.completion == 100:
            self.state = JobState.Printed

    async def when_printed(self) -> None:
        await self._update_finished_job(self.current_job)
        await self._reset_opcua_printer_job()
        await self.octo.head_jog(x=0, y=0, z=30)

        await mes.notify_pickup(self.octo.host)  # notify the matrix system to pickup

        self.current_job = None
        self.state = JobState.WaitingForPickup

    async def when_waiting_for_pickup(self) -> None:
        # do nothing
        pass

    async def when_picked(self) -> None:
        self.state = JobState.Ready

    async def when_error(self) -> None:
        logging.error("Printer is in error state")
        self.state = JobState.Connected

    async def on_cancel(self) -> None:
        match self.state:
            case JobState.Heating:
                self.state = JobState.Connecting  # wait until printer is ready
            case JobState.Printing:
                await self.octo.cancel()
                self.state = JobState.Connecting  # wait until printer is ready
            case JobState.Printed | JobState.WaitingForPickup:
                pass  # still need a pickup since printing is finished
            case state:
                logging.error("invalid cancellation when job state = %s", state)
                return

        await self._update_cancelled_job(self.current_job)
        self.current_job = None

    async def _create_job(self, order: Order) -> Job:
        async with self.session as session:
            job = Job(printer_ip=self.octo.host, order=order)
            order.status = OrderStatus.Printing

            session.add(job)
            await session.commit()
            await session.refresh(job)

            return job

    async def _update_finished_job(self, job: Job) -> None:
        job.end_time = datetime.now()
        job.order.status = OrderStatus.Finished

        async with self.session as session:
            session.add(job)
            await session.commit()

    async def _update_cancelled_job(self, job: Job) -> None:
        job.end_time = datetime.now()
        job.order.status = OrderStatus.Cancelled

        async with self.session as session:
            session.add(job)
            await session.commit()

    async def _get_job_by_id(self, job_id: int) -> Job:
        async with self.session as session:
            result = await session.exec(
                select(Job).where(Job.job_id == job_id).options(selectinload(Job.order))
            )
            return result.one()

    async def _get_current_printing_job(self) -> Job:
        async with self.session as session:
            statement = (
                select(Job)
                .join(Order)
                .where(Job.printer_ip == self.octo.host)
                .where(Order.status == OrderStatus.Printing)
                .options(selectinload(Job.order))
            )
            result = await session.exec(statement)
            return result.one()

    async def _update_opcua_printer_temp(
        self, bed: TemperatureData, nozzle: TemperatureData
    ) -> None:
        await self.opcua_printer.bed_current_temperature.set(bed.actual)
        await self.opcua_printer.bed_target_temperature.set(bed.target)
        await self.opcua_printer.nozzle_current_temperature.set(nozzle.actual)
        await self.opcua_printer.nozzle_target_temperature.set(nozzle.target)

    async def _reset_opcua_printer_job(self) -> None:
        await self.opcua_printer.job_file.set("")
        await self.opcua_printer.job_progress.set(0)
        await self.opcua_printer.job_time.set(0)
        await self.opcua_printer.job_time_left.set(0)
        await self.opcua_printer.job_time_estimate.set(0)

    async def _update_opcua_printer_job(self, job_status: CurrentJob) -> None:
        job = job_status.job
        progress = job_status.progress

        await self.opcua_printer.job_file.set(job.file.name)
        await self.opcua_printer.job_progress.set(progress.completion)
        await self.opcua_printer.job_time.set(progress.printTime)
        await self.opcua_printer.job_time_left.set(progress.printTimeLeft)
        await self.opcua_printer.job_time_estimate.set(job.estimatedPrintTime)
