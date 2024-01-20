from datetime import datetime
from http import HTTPStatus
from typing import Annotated

import aiofiles
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

from app.dependencies import ctx
from db.models import Order, User, Printer

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def unique_filename(user_id):
    return f"{user_id}-{int(datetime.now().timestamp())}"


@router.post("")
async def submit_order(
    user_id: Annotated[int, Form(title="user id", example=1)],
    printer_id: Annotated[int, Form(title="printer id", example=1)],
    file: Annotated[UploadFile, File(title="GCode file")],
):
    async with ctx.database.new_session() as session:
        if not session.exists(User, user_id):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="user not exists"
            )
        elif not session.exists(Printer, printer_id):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="printer not exists"
            )

        file_path = ctx.upload_path / unique_filename(user_id)

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        order = Order(
            user_id=user_id,
            printer_id=printer_id,
            gcode_file_path=str(file_path.absolute()),
        )
        await session.upsert(order)
        return {"id": order.id}


@router.put("/{order_id}", status_code=HTTPStatus.NO_CONTENT)
async def cancel_order(order_id: int):
    async with ctx.database.new_session() as session:
        order = await session.get(Order, order_id)

        if order is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="order not exists"
            )

        await ctx.workers[order.printer_id].cancel_job()
