class PrinterError(Exception):
    ...


class Unauthorized(PrinterError):
    ...


class FileInUse(PrinterError):
    ...


class FileAlreadyExists(PrinterError):
    ...


class NotFound(PrinterError):
    ...


class PrinterIsBusy(PrinterError):
    ...
