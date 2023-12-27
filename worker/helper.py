import math

from octo.models import TemperatureData, PrinterStateFlags
from worker import WorkerState


def is_heating_complete(temp: TemperatureData) -> bool:
    return math.fabs(temp.target - temp.actual) <= 2


def parse_printer_state(flags: PrinterStateFlags) -> WorkerState:
    if flags.ready:
        return WorkerState.Ready
    elif flags.printing:
        return WorkerState.Printing
    elif flags.error:
        return WorkerState.Error
    else:
        raise ValueError("cannot parse printer state flags to job state")
