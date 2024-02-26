__all__ = ["PrinterApi", "MockPrinter", "OctoPrinter", "PrusaPrinter", "ActualPrinter"]

from .core import PrinterApi
from .mock.core import MockPrinter
from .octo.core import OctoPrinter
from .prusa.core import PrusaPrinter

ActualPrinter = OctoPrinter | PrusaPrinter | MockPrinter
