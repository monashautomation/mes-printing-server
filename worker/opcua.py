from octo.models import TemperatureData, CurrentJob
from opcua.objects import OpcuaPrinter


class OpcuaPrinterUpdator:
    def __init__(self, opcua_printer: OpcuaPrinter):
        self.opcua_printer: OpcuaPrinter = opcua_printer

    async def update_temperature(
        self, bed: TemperatureData, nozzle: TemperatureData
    ) -> None:
        await self.opcua_printer.bed_current_temperature.set(bed.actual)
        await self.opcua_printer.bed_target_temperature.set(bed.target)
        await self.opcua_printer.nozzle_current_temperature.set(nozzle.actual)
        await self.opcua_printer.nozzle_target_temperature.set(nozzle.target)

    async def reset_current_job(self) -> None:
        await self.opcua_printer.job_file.set("")
        await self.opcua_printer.job_progress.set(0)
        await self.opcua_printer.job_time.set(0)
        await self.opcua_printer.job_time_left.set(0)
        await self.opcua_printer.job_time_estimate.set(0)

    async def update_job_progress(self, job_status: CurrentJob) -> None:
        job = job_status.job
        progress = job_status.progress

        await self.opcua_printer.job_file.set(job.file.name)
        await self.opcua_printer.job_progress.set(progress.completion)
        await self.opcua_printer.job_time.set(progress.printTime)
        await self.opcua_printer.job_time_left.set(progress.printTimeLeft)
        await self.opcua_printer.job_time_estimate.set(job.estimatedPrintTime)
