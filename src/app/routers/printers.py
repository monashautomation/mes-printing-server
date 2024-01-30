from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Form
from pydantic import HttpUrl, PositiveInt

from app.dependencies import ctx
from db.models import Printer
from printer import PrinterApi

router = APIRouter(prefix="/printers", tags=["printers"])


@router.get("")
async def all_printers() -> Sequence[Printer]:
    async with ctx.database.new_session() as session:
        return await session.all(Printer)


@router.post("")
async def add_printer(
    url: Annotated[
        HttpUrl, Form(title="URL of the printer", examples=["http://localhost:5000"])
    ],
    api_key: Annotated[
        str, Form(title="API key", examples=["79ED0684040E4B96A34C3ABF4EA0A96A"])
    ],
    opcua_ns: Annotated[
        PositiveInt,
        Form(
            title="namespace index of the OPC UA printer object",
            lt=10000,
            examples=[42],
        ),
    ],
    api: Annotated[
        PrinterApi, Form(title="Printer API", examples=["OctoPrint", "Prusa", "Mock"])
    ],
):
    printer = Printer(
        url=str(url).rstrip("/"), api_key=api_key, opcua_ns=opcua_ns, api=api
    )
    async with ctx.database.new_session() as session:
        await session.upsert(printer)
        worker = ctx.printer_worker(printer)
        worker.start()

    return {"id": printer.id}
