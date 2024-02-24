from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException
from pydantic import HttpUrl
from typing_extensions import TypedDict

from app.dependencies import ctx
from db.models import Printer
from printer import PrinterApi

router = APIRouter(prefix="/printers", tags=["printers"])


@router.get("")
async def all_printers() -> Sequence[Printer]:
    async with ctx.database.new_session() as session:
        return await session.all(Printer)


class PrinterId(TypedDict):
    id: int


@router.post("")
async def add_printer(
    url: Annotated[
        HttpUrl, Form(title="URL of the printer", examples=["http://localhost:5000"])
    ],
    api_key: Annotated[
        str, Form(title="API key", examples=["79ED0684040E4B96A34C3ABF4EA0A96A"])
    ],
    opcua_name: Annotated[
        str,
        Form(
            title="browse name of the OPC UA printer object",
            min_length=1,
            examples=["Printer1"],
        ),
    ],
    api: Annotated[
        PrinterApi, Form(title="Printer API", examples=["OctoPrint", "Prusa", "Mock"])
    ],
) -> PrinterId:
    printer = Printer(
        url=str(url).rstrip("/"), api_key=api_key, opcua_name=opcua_name, api=api
    )
    async with ctx.database.new_session() as session:
        await session.upsert(printer)
        worker = await ctx.printer_worker(printer)
        worker.start()

    assert printer.id is not None
    return PrinterId(id=printer.id)


@router.put("{printer_id}:activate", status_code=HTTPStatus.NO_CONTENT)
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


@router.put("{printer_id}:deactivate", status_code=HTTPStatus.NO_CONTENT)
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
