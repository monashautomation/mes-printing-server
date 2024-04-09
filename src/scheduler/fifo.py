from typing_extensions import override

from db import session, DatabaseSession
from db.models import JobStatus
from service import JobService, PrinterService
from task import PeriodicTask


class FifoScheduler(PeriodicTask):
    def __init__(self):
        super().__init__(interval_secs=60)
        self.db: DatabaseSession = session()
        self.printer_service = PrinterService(self.db)
        self.job_service: JobService = JobService(self.db)

    async def schedule(self) -> None:
        unscheduled = await self.job_service.unscheduled_jobs()

        if len(unscheduled) == 0:
            return

        occupied_printer_ids = {
            job.printer_id for job in await self.job_service.scheduled_jobs()
        }

        idle_printer_ids = [
            printer.id
            for printer in await self.printer_service.get_printers(has_worker=True)
            if printer.id not in occupied_printer_ids
        ]

        if len(idle_printer_ids) == 0:
            return

        job, printer_id = unscheduled[0], idle_printer_ids[0]
        self.logger.info("schedule job (id=%d) to printer (id=%d)", job, printer_id)

        job.printer_id = printer_id
        await self.job_service.update_job(job, JobStatus.Scheduled)

    @override
    async def step(self) -> None:
        await self.schedule()
