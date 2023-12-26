class CannotPrint(RuntimeError):
    def __init__(self):
        super().__init__("printer is not operational or is printing")


class InvalidUploadParam(ValueError):
    def __init__(self):
        super().__init__("invalid param")


class InvalidConnectionParam(ValueError):
    def __init__(self):
        super().__init__("selected port or baudrate is not available")


class InvalidAxis(ValueError):
    pass


class InvalidUploadLocation(ValueError):
    pass


class InvalidFileExtension(ValueError):
    def __init__(self):
        super().__init__("file must be a gcode or stl")
