from datetime import datetime
from http import HTTPStatus
from typing import Annotated

import aiofiles
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

from app.dependencies import ctx
from db.models import Order, User

router = APIRouter(prefix="/orders", tags=["orders"])


def unique_filename(user_id):
    return f"{user_id}-{int(datetime.now().timestamp())}.gcode"


@router.post("")
async def submit_order(
    user_id: Annotated[str, Form(title="user id", example=1)],
    file: Annotated[UploadFile, File(title="GCode file")],
):
    async with ctx.database.new_session() as session:
        if not await session.exists(User, user_id):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="user not exist"
            )

        file_path = ctx.upload_path / unique_filename(user_id)

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        order = Order(
            user_id=user_id,
            gcode_file_path=str(file_path.absolute()),
        )
        await session.upsert(order)
        return {"id": order.id}


@router.put("/{order_id}:approve")
async def approve_order(order_id: int, user_id: str):
    async with ctx.database.new_session() as session:
        user = await session.get(User, user_id)

        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="user not exist"
            )
        elif user.permission != "admin":
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail="user must be an admin"
            )

        order = await session.get(Order, order_id)

        if order is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="order not exist"
            )

        await session.approve_order(order)
    return {"approved": True}


@router.put("/{order_id}:cancel", status_code=HTTPStatus.NO_CONTENT)
async def cancel_order(order_id: int):
    async with ctx.database.new_session() as session:
        order = await session.get(Order, order_id)

        if order is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="order not exist"
            )

        await ctx.workers[order.printer_id].cancel_job()


@router.get("/{order_id}")
async def order_details(order_id: int) -> Order:
    async with ctx.database.new_session() as session:
        order = await session.get(Order, order_id)

        if order is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="order not exist"
            )
        return order
