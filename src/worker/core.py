from datetime import datetime

import httpx
from mes_opcua_server.models import Printer as OpcuaPrinter
from pydantic import HttpUrl
from typing_extensions import override

from db.models import Job, JobStatus, Printer
from printer import ActualPrinter
from printer.models import PrinterStatus, LatestJob
from service import JobService, opcua_service
from setting import app_settings
from task import PeriodicTask


class LatestPrinterStatus(PrinterStatus):
    name: str
    model: str
    url: HttpUrl
    camera_url: str | None


def is_same_job(prev: Job, cur: LatestJob) -> bool:
    if prev.start_time is None:
        return False

    if cur.start_time < prev.start_time:  # time has slight diff on ms
        dt = prev.start_time - cur.start_time
    else:
        dt = cur.start_time - prev.start_time

    secs = dt.seconds
    return prev.printer_filename == cur.file_path and secs <= 10


class PrinterWorker(PeriodicTask):
    def __init__(
        self,
        printer: Printer,
        api: ActualPrinter,
        opcua_printer: OpcuaPrinter | None = None,
        job_service: JobService | None = None,
    ) -> None:
        PeriodicTask.__init__(
            self,
            interval_secs=app_settings.printer_worker_interval,
            name=f"PrinterWorker{printer.id}",
        )

        self.job_service: JobService = job_service or JobService()

        self.printer: Printer = printer
        self.api: ActualPrinter = api
        self.opcua_printer: OpcuaPrinter | None = opcua_printer

        self._cache_update_time: datetime = datetime.min
        self._status_cache: LatestPrinterStatus | None = None

    @override
    async def step(self) -> None:
        try:
            stat = await self.printer_status()

            if stat is None:
                return

            if self.opcua_printer is not None:
                await self._update_opcua(stat)

            job = await self.job_service.current_printer_job(self.printer.id)
            await self.handle_status(job, stat)
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "get error response, status code=%d, url=%s",
                e.response.status_code,
                e.request.url,
            )
        except httpx.HTTPError as e:
            self.logger.error(
                "http request failed, url=%s, error type=%s", e.request.url, type(e)
            )

    async def handle_status(self, job: Job | None, stat: LatestPrinterStatus) -> None:
        if stat.is_error:
            self.logger.error("printer has an error, try again in next iteration")
            return

        match job, stat:
            case None, PrinterStatus(is_ready=True):
                self.logger.debug("printer is ready and no job is available")
            case None, PrinterStatus(is_printing=True):
                self.logger.info("persisting new job submitted through printer")
                await self._new_job(stat)
            case Job() as job, PrinterStatus() as stat if is_same_job(job, stat.job):
                if job.need_pickup():
                    await self.require_pickup(job)
                elif job.need_cancel():
                    await self.on_cancel(job)
                elif job.is_printing():
                    await self.when_printing(job, stat)
                # do nothing if job is already printed
            case Job() as job, _ as printer:
                if job.is_pending() and printer.is_ready:
                    await self.when_ready(job)
                else:
                    # printer is doing another job
                    self.logger.info(
                        "finish prev job since printer is doing another job %s",
                        printer.job,
                    )
                    await self.on_pick(job)
            case _, _:
                self.logger.error("unhandled status job=%s, stat=%s", job, stat)

    async def _new_job(self, stat: LatestPrinterStatus) -> None:
        assert stat.is_printing and stat.job is not None

        job = Job(
            printer_id=self.printer.id,
            from_server=False,
            status=(JobStatus.Printing | JobStatus.Scheduled).value,
            printer_filename=stat.job.file_path,
            start_time=stat.job.start_time,
        )
        await self.job_service.create_job(job)

    async def when_ready(self, job: Job) -> None:
        if job is None or not job.from_server:
            return
        assert job.gcode_file_path is not None

        self.logger.info("start printing job (id=%d) from server", job.id)

        await self.api.upload_file(job.gcode_file_path)
        await self.api.start_job(job.gcode_file_path)

        job.start_time = datetime.now()
        await self.job_service.update_job(job, JobStatus.Printing)

    async def when_printing(self, job: Job, stat: LatestPrinterStatus) -> None:
        self.logger.info(
            "printing job progress %.2f%% (id=%d)", stat.job_progress_or_zero(), job.id
        )
        if stat.job is None or stat.job.done:
            await self.job_service.update_job(job, JobStatus.Printed)

    async def when_printed(self, job: Job) -> None:
        self.logger.info("printing job is finished (id=%d)", job.id)
        if job.from_server:
            filename = job.gcode_filename()
            assert filename is not None
            await self.api.delete_file(filename)

        await self.require_pickup(job)

    async def on_pick(self, job: Job) -> None:
        self.logger.info("mark job as picked (id=%d)", job.id)
        await self.job_service.update_job(job, JobStatus.Picked)

    async def on_cancel(self, job: Job) -> None:
        if job.is_printing():
            self.logger.info("cancelling printing job (id=%d)", job.id)
            await self.api.stop_job()

        await self.job_service.update_job(job, JobStatus.Cancelled)

    async def require_pickup(self, job: Job) -> None:
        self.logger.warning("simulate sending pickup request to robots")
        await self.job_service.update_job(job, JobStatus.PickupIssued)

    async def printer_status(self) -> LatestPrinterStatus | None:
        delta = datetime.now() - self._cache_update_time
        if delta.seconds < self.interval_secs:
            return self._status_cache

        try:
            stat = await self.api.current_status()
        except httpx.HTTPError as e:
            self.logger.error("cannot get printer status, error type=%s", type(e))
            self._status_cache = None
            return None

        self._cache_update_time = datetime.now()
        self._status_cache = LatestPrinterStatus(
            **stat.model_dump(),
            name=self.printer.opcua_name or "",
            model=self.printer.model or str(self.printer.api),
            url=HttpUrl(self.printer.url),
            camera_url=self.printer.camera_url,
        )

        return self._status_cache

    async def _update_opcua(self, stat: LatestPrinterStatus) -> None:
        assert self.opcua_printer is not None

        bed, nozzle, job = stat.temp_bed, stat.temp_nozzle, stat.job

        self.opcua_printer.url = stat.url
        self.opcua_printer.update_time = datetime.now()
        self.opcua_printer.state = stat.state
        self.opcua_printer.bed.target = bed.target
        self.opcua_printer.bed.actual = bed.actual
        self.opcua_printer.nozzle.target = nozzle.target
        self.opcua_printer.nozzle.actual = nozzle.actual
        self.opcua_printer.camera_url = HttpUrl(stat.camera_url or "http://unknown")
        self.opcua_printer.model = stat.model

        if job is not None:
            self.opcua_printer.job.file = job.file_path
            self.opcua_printer.job.progress = job.progress or 0
            self.opcua_printer.job.time_used = job.time_used or 0
            self.opcua_printer.job.time_left = job.time_left or 0
            self.opcua_printer.job.time_left_approx = job.time_approx or 0

        await opcua_service.commit()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.job_service.__aexit__(exc_type, exc_val, exc_tb)
