import secrets
from collections.abc import Sequence
from pathlib import Path

import aiofiles
from sqlalchemy import true, ColumnOperators
from sqlmodel import select, null

from db.models import Job, JobStatus, JobHistory
from setting import app_settings
from .db import BaseDbService


class JobService(BaseDbService):
    async def get_job(
        self, job_id: int | None = None, printer_filename: str | None = None
    ) -> Job:
        """
        Get a job.
        :param printer_filename: filename returned by printer
        :param job_id: job id
        :return: target job
        """
        if job_id is None and printer_filename is None:
            raise ValueError("at least one criteria should not be None")

        stmt = select(Job)

        if job_id is not None:
            stmt = stmt.where(Job.id == job_id)

        if printer_filename is not None:
            stmt = stmt.where(Job.printer_filename == printer_filename)

        result = await self.db.exec(stmt)
        return result.one()

    async def get_job_history(self, job_id: int) -> Sequence[JobHistory]:
        stmt = select(JobHistory).where(JobHistory.job_id == job_id)
        result = await self.db.exec(stmt)
        return result.all()

    async def create_job(self, job: Job) -> None:
        self.db.add(job)
        await self.db.commit()

    async def unapproved_jobs(self) -> Sequence[Job]:
        """
        Get jobs that haven't been approved.
        :return: a list of unapproved jobs
        """
        stmt = select(Job).where(Job.status < JobStatus.Approved.value)
        result = await self.db.exec(stmt)
        return result.all()

    async def unscheduled_jobs(self) -> Sequence[Job]:
        """
        Get jobs that is submitted from server, and have been approved
        but haven't been assigned a printer.
        :return: a list of pending jobs
        """
        stmt = select(Job).where(
            Job.status == JobStatus.ToSchedule.value,
            Job.printer_id == null(),
            Job.from_server == true(),
        )
        result = await self.db.exec(stmt)
        return result.all()

    async def scheduled_jobs(self) -> Sequence[Job]:
        """
        Get jobs that have been scheduled but haven't been printed.
        :return: a list of pending jobs
        """
        stmt = select(Job).where(
            Job.status == JobStatus.ToPrint.value, Job.printer_id != null()
        )
        result = await self.db.exec(stmt)
        return result.all()

    async def next_pending_job(self, printer_id: int) -> Job | None:
        """
        Get the next pending job of the printer.
        A pending job should be approved and assigned to the printer, but hasn't been printed.

        **Note**: The scheduler should keep only one pending job for each printer,
        otherwise the one with the smallest id will be returned.
        :param printer_id: printer id
        :return: a pending job
        """
        stmt = select(Job).where(
            Job.status == JobStatus.ToPrint.value, Job.printer_id == printer_id
        )
        result = await self.db.exec(stmt)
        return result.first()

    async def current_printer_job(self, printer_id: int) -> Job | None:
        """
        Get the current job of the printer.
        The current job may have been cancelled but is still on bed (not picked).
        :param printer_id: printer id
        :return: a Job instance or None
        """
        assert isinstance(Job.status, ColumnOperators)

        stmt = select(Job).where(
            Job.printer_id == printer_id,
            Job.status > JobStatus.Scheduled.value,
            Job.status.bitwise_and(JobStatus.Picked.value) == 0,
        )
        result = await self.db.exec(stmt)
        return result.one_or_none()

    async def update_job(
        self, job: Job, new_stats_flag: JobStatus | None = None
    ) -> None:
        """
        Update job status and insert a job history record.
        :param job: a Job instance which must be managed by the db session of this service
        :param new_stats_flag: new job status that will be added to the bitmask
        """
        if new_stats_flag is not None:
            job.add_status_flag(new_stats_flag)
            history = JobHistory(job_id=job.id, status=str(new_stats_flag))
            self.db.add(history)

        self.db.add(job)

        await self.db.commit()

    @staticmethod
    def generate_filename() -> str:
        """
        Generate a unique filename for gcode file persistence.

        Current implementation provides 16777216 (16 ** 6) names.
        :return: filename without extension
        """
        return f"server-{secrets.token_hex(6)}"

    async def save_gcode_file(self, filename: str, content: bytes) -> Path:
        filename = self.generate_filename() + Path(filename).suffix
        file_path = app_settings.upload_path / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return file_path
