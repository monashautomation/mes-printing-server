from mes_opcua_server.models import Printer as OpcuaPrinter
from pydantic import BaseModel


class ExtraPrinterData(BaseModel):
    camera_url: str = "http://localhost"
    model: str = "Prusa XL"


extra_data: dict[str, ExtraPrinterData] = {
    "Printer0": ExtraPrinterData(
        model="Prusa XL 5 heads", camera_url="http://172.32.1.90:8080/?action=stream"
    ),
    "Printer1": ExtraPrinterData(
        model="Prusa XL 2 heads", camera_url="http://172.32.1.91:8080/?action=stream"
    ),
    "Printer2": ExtraPrinterData(
        model="Prusa XL 1 head", camera_url="http://172.32.1.92:8080/?action=stream"
    ),
    "Printer3": ExtraPrinterData(
        model="Prusa XL 1 head", camera_url="http://172.32.1.93:8080/?action=stream"
    ),
    "Printer4": ExtraPrinterData(
        model="Prusa XL 1 head", camera_url="http://172.32.1.94:8080/?action=stream"
    ),
    "Printer5": ExtraPrinterData(
        model="Prusa XL 1 head", camera_url="http://172.32.1.95:8080/?action=stream"
    ),
    "Printer6": ExtraPrinterData(
        model="Prusa XL 1 head", camera_url="http://172.32.1.96:8080/?action=stream"
    ),
    "Printer7": ExtraPrinterData(
        model="Prusa XL 1 head", camera_url="http://172.32.1.97:8080/?action=stream"
    ),
}


def update_hardcoded_data(name: str, printer: OpcuaPrinter):
    # hardcode for now, will be replaced in a proper way

    if name in extra_data:
        extra = extra_data[name]
        printer.camera_url = extra.camera_url
        printer.model = extra.model
