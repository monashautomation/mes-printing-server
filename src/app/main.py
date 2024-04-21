from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import filament, jobs, printers
from db import database
from service import PrinterService, opcua_service
from worker.manager import start_new_printer_worker


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    await database.create_tables()
    await opcua_service.connect()

    async with PrinterService() as service:
        for printer in await service.get_printers(has_worker=True):
            await start_new_printer_worker(printer)

    yield

    await database.close()


app = FastAPI(
    title="MES Printing Server",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

root_router = APIRouter(prefix="/api/v1")
root_router.include_router(printers.router)
root_router.include_router(jobs.router)
root_router.include_router(filament.router)

app.include_router(root_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
