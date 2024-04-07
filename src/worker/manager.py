import logging

from db.models import Printer
from printer import create_printer
from service import opcua_service
from .core import PrinterWorker, LatestPrinterStatus

PrinterId = int

printer_workers: dict[PrinterId, PrinterWorker] = {}

_logger = logging.getLogger("worker.manager")


async def create_printer_worker(printer: Printer) -> PrinterWorker:
    api = create_printer(api=printer.api, url=printer.url, api_key=printer.api_key)

    opcua = None
    if printer.opcua_name is not None:
        opcua = await opcua_service.get_printer(printer.opcua_name)

    return PrinterWorker(printer=printer, opcua_printer=opcua, api=api)


def get_printer_worker(printer_id: int) -> PrinterWorker | None:
    return printer_workers.get(printer_id, None)


async def get_printer_status(printer_id: int) -> LatestPrinterStatus | None:
    worker = get_printer_worker(printer_id)

    if worker is None:
        return None

    return await worker.printer_status()


async def start_new_printer_worker(printer: Printer) -> None:
    if printer.id in printer_workers:
        return

    worker = await create_printer_worker(printer)
    printer_workers[printer.id] = worker
    worker.start()


def stop_printer_worker(printer_id: int) -> None:
    if printer_id not in printer_workers:
        return

    worker = printer_workers.pop(printer_id)
    worker.stop()
