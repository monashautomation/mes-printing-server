import pytest
import pytest_asyncio

from db.models import Job, JobStatus
from service import JobService


@pytest.fixture
def new_job() -> Job:
    return Job(from_server=True, original_filename="1.gcode")


@pytest.fixture
def approved_job() -> Job:
    return Job(
        from_server=True,
        status=(JobStatus.Created | JobStatus.Approved).value,
        original_filename="2.gcode",
    )


@pytest.fixture
def scheduled_job() -> Job:
    return Job(
        from_server=True,
        printer_id=1,
        status=(JobStatus.Created | JobStatus.Approved | JobStatus.Scheduled).value,
        original_filename="3.gcode",
    )


@pytest.fixture
def printing_job() -> Job:
    return Job(
        from_server=True,
        printer_id=2,
        status=(
            JobStatus.Created
            | JobStatus.Approved
            | JobStatus.Scheduled
            | JobStatus.Printing
        ).value,
        original_filename="4.gcode",
    )


@pytest_asyncio.fixture(autouse=True)
async def prepare_jobs(
    job_service: JobService,
    new_job: Job,
    approved_job: Job,
    scheduled_job: Job,
    printing_job: Job,
) -> None:
    await job_service.create_job(new_job)
    await job_service.create_job(approved_job)
    await job_service.create_job(scheduled_job)
    await job_service.create_job(printing_job)


async def test_get_job_by_id(job_service: JobService, new_job: Job) -> None:
    job = await job_service.get_job(job_id=new_job.id)
    assert job.id == new_job.id
    assert job.original_filename == new_job.original_filename
    assert job.flag() == JobStatus.Created


async def test_unapproved_jobs(job_service: JobService, new_job: Job) -> None:
    jobs = await job_service.unapproved_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == new_job.id


async def test_approved_jobs(job_service: JobService, approved_job: Job) -> None:
    jobs = await job_service.unscheduled_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == approved_job.id


async def test_scheduled_jobs(job_service: JobService, scheduled_job: Job) -> None:
    jobs = await job_service.scheduled_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == scheduled_job.id


async def test_next_pending_job(job_service: JobService, scheduled_job: Job) -> None:
    job = await job_service.next_pending_job(printer_id=scheduled_job.printer_id)

    assert job is not None
    assert job.id == scheduled_job.id


async def test_current_printer_job(job_service: JobService, printing_job: Job) -> None:
    job = await job_service.current_printer_job(printer_id=printing_job.printer_id)

    assert job is not None
    assert job.id == printing_job.id


async def test_approve_job(job_service: JobService, new_job: Job) -> None:
    await job_service.update_job(new_job, JobStatus.Approved)
    assert new_job.flag() == JobStatus.Created | JobStatus.Approved
