from collections.abc import Sequence

from sqlmodel import select

from .db import BaseDbService
from db.models import Printer


class PrinterService(BaseDbService):
    async def get_printers(
        self, group_name: str | None = None, has_worker: bool | None = None
    ) -> Sequence[Printer]:
        stmt = select(Printer)

        if group_name is not None:
            stmt = stmt.where(Printer.group_name == group_name)
        if has_worker is not None:
            stmt = stmt.where(Printer.has_worker == has_worker)

        result = await self.db.exec(stmt)
        return result.all()

    async def get_printer(
        self,
        printer_id: int | None = None,
        group_name: str | None = None,
        opcua_name: str | None = None,
    ) -> Printer | None:
        stmt = select(Printer)

        if printer_id is not None:
            stmt = stmt.where(Printer.id == printer_id)
        if group_name is not None:
            stmt = stmt.where(Printer.group_name == group_name)
        if opcua_name is not None:
            stmt = stmt.where(Printer.opcua_name == opcua_name)

        result = await self.db.exec(stmt)
        return result.one_or_none()

    async def create_printer(self, printer: Printer) -> None:
        await self.db.upsert(printer)

    async def update_printer(self, printer: Printer) -> None:
        await self.db.upsert(printer)
