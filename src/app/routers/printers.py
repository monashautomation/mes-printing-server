from typing import Sequence

from fastapi import APIRouter
from pydantic import BaseModel, Field, AnyUrl

from app.dependencies import app_ctx
from db.models import Printer

router = APIRouter(prefix="/api/v1/printers", tags=["printers"])


@router.get("/")
async def all_printers() -> Sequence[Printer]:
    return await app_ctx.session.all(Printer)


class CreatePrinter(BaseModel):
    octo_url: AnyUrl = Field(
        title="octoprint server URL", examples=["http://localhost:5000"]
    )
    octo_api_key: str = Field(
        title="octoprint API key",
        examples=["79ED0684040E4B96A34C3ABF4EA0A96A"],
        min_length=1,
    )
    opcua_ns: int = Field(
        description="OPCUA printer object namespace index", examples=[1], gt=0
    )


@router.post("")
async def add_printer(model: CreatePrinter):
    printer = Printer(
        octo_url=str(model.octo_url),
        octo_api_key=model.octo_api_key,
        opcua_ns=model.opcua_ns,
    )
    await app_ctx.session.upsert(printer)
    return {"id": printer.id}
