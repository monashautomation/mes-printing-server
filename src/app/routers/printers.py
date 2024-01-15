from typing import Sequence, Annotated

from fastapi import APIRouter, Form
from pydantic import AnyUrl, PositiveInt

from app.dependencies import app_ctx
from db.models import Printer

router = APIRouter(prefix="/api/v1/printers", tags=["printers"])


@router.get("/")
async def all_printers() -> Sequence[Printer]:
    return await app_ctx.session.all(Printer)


@router.post("")
async def add_printer(
    octo_url: Annotated[
        AnyUrl, Form(title="OctoPrint server URL", example="http://localhost:5000")
    ],
    octo_api_key: Annotated[
        str, Form(title="OctoPrint API key", example="79ED0684040E4B96A34C3ABF4EA0A96A")
    ],
    opcua_ns: Annotated[
        PositiveInt,
        Form(
            title="namespace index of the OPC UA printer object",
            lt=10000,
            example=42,
        ),
    ],
):
    printer = Printer(
        octo_url=str(octo_url),
        octo_api_key=octo_api_key,
        opcua_ns=opcua_ns,
    )
    await app_ctx.session.upsert(printer)
    return {"id": printer.id}
