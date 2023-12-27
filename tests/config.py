from enum import StrEnum


class PrinterHost(StrEnum):
    Host1 = "192.168.228.1"
    Host2 = "192.168.228.2"
    Host3 = "192.168.228.3"


class GcodeFile(StrEnum):
    A = "A.gcode"
    B = "B.gcode"
    C = "C.gcode"
