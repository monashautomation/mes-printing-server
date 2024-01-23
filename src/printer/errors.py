class Unauthorized(Exception):
    ...


class FileInUse(ValueError):
    ...


class FileAlreadyExists(ValueError):
    ...


class NotFound(ValueError):
    ...


class PrinterIsBusy(ValueError):
    ...
