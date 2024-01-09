import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.dependencies import app_ctx
from app.routers import printers, orders


@asynccontextmanager
async def lifespan(app: FastAPI):
    await app_ctx.load()
    worker_tasks = [
        asyncio.create_task(worker.run(), name=f"printer-worker-{worker.printer_id}")
        for worker in app_ctx.printer_workers
    ]
    yield
    for task in worker_tasks:
        task.cancel()
    await app_ctx.close()


app = FastAPI()
app.include_router(printers.router)
app.include_router(orders.router)
