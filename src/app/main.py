from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import ctx
from app.routers import orders, printers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with ctx:
        await ctx.start_printer_workers()
        yield


app = FastAPI(
    title="Printing Server",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

root_router = APIRouter(prefix="/api/v1")
root_router.include_router(printers.router)
root_router.include_router(orders.router)

app.include_router(root_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
