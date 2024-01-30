from . import OpcuaFloatVar, OpcuaStrVar
from .core import OpcuaObject, OpcuaVariable


class PrinterHead(OpcuaObject):
    x: OpcuaVariable[float] = OpcuaFloatVar(name="X")
    y: OpcuaVariable[float] = OpcuaFloatVar(name="Y")
    z: OpcuaVariable[float] = OpcuaFloatVar(name="Z")


class PrinterJob(OpcuaObject):
    file: OpcuaVariable[str] = OpcuaStrVar(name="File")
    progress: OpcuaVariable[float] = OpcuaFloatVar(name="Progress")
    time_left: OpcuaVariable[float] = OpcuaFloatVar(name="TimeLeft")
    time_left_approx: OpcuaVariable[float] = OpcuaFloatVar(name="TimeLeftApprox")
    time_used: OpcuaVariable[float] = OpcuaFloatVar(name="TimeUsed")


class OpcuaPrinter(OpcuaObject):
    state: OpcuaVariable[str] = OpcuaStrVar(name="State")
    noz_act_temp: OpcuaVariable[float] = OpcuaFloatVar(name="NozzleActualTemperature")
    bed_act_temp: OpcuaVariable[float] = OpcuaFloatVar(name="BedActualTemperature")
    noz_tar_temp: OpcuaVariable[float] = OpcuaFloatVar(name="NozzleTargetTemperature")
    bed_tar_temp: OpcuaVariable[float] = OpcuaFloatVar(name="BedTargetTemperature")

    head: PrinterHead = PrinterHead(name="Head")
    job: PrinterJob = PrinterJob(name="LatestJob")
