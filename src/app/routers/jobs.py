from collections.abc import Sequence
from http import HTTPStatus
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from db.models import Job, JobStatus, JobHistory
from service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobDetails(BaseModel):
    job: Job
    history: Sequence[JobHistory]


@router.get("/{job_id}")
async def get_job(job_id: int) -> JobDetails:
    async with JobService() as service:
        job = await service.get_job(job_id=job_id)
        history = await service.get_job_history(job_id)

        return JobDetails(job=job, history=history)


@router.post("")
async def submit_job(
    user_id: Annotated[str, Form(title="user id", examples=["google|3fse56a2"])],
    file: Annotated[UploadFile, File(title="GCode file")],
    printer_id: Annotated[int | None, Form(title="printer id")] = None,
) -> None:
    filename = file.filename or ""

    if Path(filename).suffix not in (".gcode", ".bgcode"):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="invalid file extension, must be .gcode or .bgcode",
        )

    async with JobService() as service:
        file_path = await service.save_gcode_file(filename, await file.read())

        job = Job(
            user_id=user_id,
            printer_id=printer_id,
            from_server=True,
            gcode_file_path=str(file_path),
        )

        await service.create_job(job)


@router.put("/{job_id}:approve", status_code=HTTPStatus.ACCEPTED)
async def approve_order(job_id: int) -> None:
    async with JobService() as service:
        job = await service.get_job(job_id)
        await service.update_job(job, JobStatus.Approved)


@router.put("/{job_id}:cancel", status_code=HTTPStatus.ACCEPTED)
async def cancel_order(job_id: int) -> None:
    async with JobService() as service:
        job = await service.get_job(job_id)
        await service.update_job(job, JobStatus.CancelIssued)


# TODO: pickup job, validate by job status(cancelled or printed)
