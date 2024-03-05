from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.dependencies import ctx
from worker import PrinterState

router = APIRouter(prefix="/printer", tags=["printer"])


@router.get("/{printer_name}/state")
async def printer_state(printer_name: str) -> PrinterState:
    target = [
        worker
        for worker in ctx.workers.values()
        if worker.printer.opcua_name == printer_name
    ]
    if len(target) != 1:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="printer not exist"
        )

    [worker] = target
    return await worker.latest_state()


@router.get(
    "/{printer_name}/job/thumbnail",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
async def printer_job_previewed_model(printer_name: str) -> Response:
    target = [
        worker
        for worker in ctx.workers.values()
        if worker.printer.opcua_name == printer_name
    ]
    if len(target) != 1:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="printer not exist"
        )

    [worker] = target
    # client must log in the Prusa printer to download the thumbnail
    image_bytes = await worker.previewed_model()
    return Response(content=image_bytes, media_type="image/png")
