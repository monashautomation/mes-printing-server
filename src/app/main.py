from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import ctx
from app.routers import printers, orders

origins = [
    "http://localhost",
    "http://localhost:3000",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with ctx:
        await ctx.start_printer_workers()
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(printers.router)
app.include_router(orders.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
