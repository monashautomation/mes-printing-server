from collections.abc import Sequence
from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from typing_extensions import TypedDict

from app.dependencies import ctx
from db.models import Printer
from printer import PrinterApi
from worker import PrinterState

router = APIRouter(prefix="/printers", tags=["printers"])


@router.get("")
async def all_printers() -> Sequence[Printer]:
    async with ctx.database.new_session() as session:
        return await session.all(Printer)


class PrinterId(TypedDict):
    id: int


class CreatePrinter(BaseModel):
    url: HttpUrl = Field(title="URL of the printer", examples=["http://localhost:5000"])
    api_key: str = Field(title="API key", examples=["79ED0684040E4B96A34C3ABF4EA0A96A"])
    opcua_name: str = Field(
        title="browse name of the OPC UA printer object",
        min_length=1,
        examples=["Printer1"],
    )
    api: PrinterApi = Field(
        title="Printer API", examples=["OctoPrint", "Prusa", "Mock"]
    )


@router.post("")
async def add_printer(model: CreatePrinter) -> PrinterId:
    printer = Printer(
        url=str(model.url).rstrip("/"),
        api_key=model.api_key,
        opcua_name=model.opcua_name,
        api=model.api,
    )
    async with ctx.database.new_session() as session:
        await session.upsert(printer)
        worker = await ctx.printer_worker(printer)
        worker.start()

    assert printer.id is not None
    return PrinterId(id=printer.id)


@router.put("/{printer_id}:activate", status_code=HTTPStatus.NO_CONTENT)
async def activate_printer(printer_id: int) -> None:
    async with ctx.database.new_session() as session:
        printer = await session.get(Printer, printer_id)

        if printer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="printer not exist"
            )

        printer.is_active = True
        await session.upsert(printer)
        await ctx.start_printer_worker(printer)


@router.put("/{printer_id}:deactivate", status_code=HTTPStatus.NO_CONTENT)
async def deactivate_printer(printer_id: int) -> None:
    async with ctx.database.new_session() as session:
        printer = await session.get(Printer, printer_id)

        if printer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="printer not exist"
            )

        printer.is_active = False
        await session.upsert(printer)
        await ctx.stop_printer_worker(printer)


@router.get("/state/{printer_name}")
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
