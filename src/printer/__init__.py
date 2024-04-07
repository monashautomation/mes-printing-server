__all__ = [
    "PrinterApi",
    "MockPrinter",
    "OctoPrinter",
    "PrusaPrinter",
    "ActualPrinter",
    "create_printer",
]

from setting import app_settings
from .core import PrinterApi
from .mock.core import MockPrinter
from .octo.core import OctoPrinter
from .prusa.core import PrusaPrinter

ActualPrinter = OctoPrinter | PrusaPrinter | MockPrinter


def create_printer(api: PrinterApi, url: str, api_key: str | None) -> ActualPrinter:
    match api:
        case PrinterApi.OctoPrint:
            return OctoPrinter(url=url, api_key=api_key)
        case PrinterApi.PrusaLink:
            return PrusaPrinter(url=url, api_key=api_key)
        case PrinterApi.Mock:
            return MockPrinter(
                url=url,
                api_key=api_key,
                interval=app_settings.mock_printer_interval,
                job_time=app_settings.mock_printer_job_time,
            )
        case _:
            raise NotImplementedError
