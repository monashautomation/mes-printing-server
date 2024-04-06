from collections.abc import Sequence
from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from starlette.responses import RedirectResponse

from db.models import Printer
from printer import PrinterApi
from service import PrinterService
from worker import LatestPrinterStatus, manager

router = APIRouter(prefix="/printers", tags=["printers"])


class HttpPrinterService(PrinterService):
    async def get_printer(
        self,
        printer_id: int | None = None,
        group_name: str | None = None,
        opcua_name: str | None = None,
    ) -> Printer:
        printer = await super().get_printer(
            printer_id=printer_id, group_name=group_name, opcua_name=opcua_name
        )

        if printer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="printer not exist"
            )

        return printer


@router.get("")
async def get_printers(group: str | None = None) -> Sequence[Printer]:
    async with HttpPrinterService() as service:
        return await service.get_printers(group_name=group)


@router.get("/{printer_id}")
async def get_printer_by_id(printer_id: int) -> Printer:
    async with HttpPrinterService() as service:
        return await service.get_printer(printer_id=printer_id)


@router.get("/{printer_id}/status")
async def get_printer_status_by_id(printer_id: int) -> LatestPrinterStatus | None:
    async with HttpPrinterService() as service:
        printer = await service.get_printer(printer_id=printer_id)

        worker = manager.get_printer_worker(printer.id)

        if worker is None:
            return None

        return await worker.printer_status()


@router.get("/opcua/{name}")
async def get_printer_by_opcua_name(name: str) -> Printer:
    async with HttpPrinterService() as service:
        return await service.get_printer(opcua_name=name)


@router.get("/opcua/{name}/status")
async def get_printer_status_by_opcua_name(name: str) -> LatestPrinterStatus | None:
    async with HttpPrinterService() as service:
        printer = await service.get_printer(opcua_name=name)

        worker = manager.get_printer_worker(printer.id)

        if worker is None:
            return None

        return await worker.printer_status()


@router.get("/opcua/{name}/preview")
async def get_model_preview_by_opcua_name(name: str) -> RedirectResponse:
    async with HttpPrinterService() as service:
        printer = await service.get_printer(opcua_name=name)

        stat = await manager.get_printer_status(printer.id)

        if stat is None or stat.job is None or stat.job.previewed_model_url is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="no preview available"
            )

        return RedirectResponse(url=stat.job.previewed_model_url)


class CreatePrinter(BaseModel):
    url: HttpUrl = Field(title="URL of the printer", examples=["http://localhost:5000"])
    camera_url: HttpUrl | None = Field(
        title="URL of the printer camera",
        examples=["http://localhost:8080/?action=stream"],
    )
    api_key: str = Field(title="API key", examples=["79ED0684040E4B96A34C3ABF4EA0A96A"])
    group: str | None = Field(
        default=None,
        title="Group name of the printer",
        examples=["lab", "1st-year-learning-center"],
    )
    opcua_name: str | None = Field(
        default=None,
        title="browse name of the OPC UA printer object",
        min_length=1,
        examples=["Printer1"],
    )
    api: PrinterApi = Field(
        title="Printer API", examples=["OctoPrint", "Prusa", "Mock"]
    )
    worker: bool = Field(title="Run a printer worker or not")
    model: str | None = Field(
        title="model of the printer", examples=["Prusa XL 2 Heads"]
    )


@router.post("", status_code=HTTPStatus.CREATED)
async def add_printer(model: CreatePrinter) -> None:
    printer = Printer(
        group_name=model.group,
        url=str(model.url).rstrip("/"),
        camera_url=str(model.camera_url),
        api_key=model.api_key,
        opcua_name=model.opcua_name,
        api=model.api,
        has_worker=model.worker,
        model=model.model,
    )
    async with HttpPrinterService() as service:
        await service.create_printer(printer)

        if printer.has_worker:
            await manager.start_new_printer_worker(printer)


@router.put("/{printer_id}/worker:start", status_code=HTTPStatus.NO_CONTENT)
async def start_printer_worker(printer_id: int) -> None:
    async with HttpPrinterService() as service:
        printer = await service.get_printer(printer_id=printer_id)

        if not printer.has_worker:
            printer.has_worker = True
            await service.update_printer(printer)
            await manager.start_new_printer_worker(printer)


@router.put("/{printer_id}/worker:stop", status_code=HTTPStatus.NO_CONTENT)
async def stop_printer_worker(printer_id: int) -> None:
    async with HttpPrinterService() as service:
        printer = await service.get_printer(printer_id=printer_id)

        if printer.has_worker:
            printer.has_worker = False
            await service.update_printer(printer)
            manager.stop_printer_worker(printer_id)
