from opcuax.types import OpcuaObject, AsyncMutator, OpcuaVariable


class OpcuaPrinter(OpcuaObject):
    program_id: AsyncMutator[int] = OpcuaVariable(name="progID", default=0)
    start: AsyncMutator[bool] = OpcuaVariable(name="start", default=False)

    part_removed: AsyncMutator[bool] = OpcuaVariable(
        name="Pc_PartRemoved", default=False
    )
    bed_cleaned: AsyncMutator[bool] = OpcuaVariable(name="Pc_BedCleaned", default=False)

    file: AsyncMutator[str] = OpcuaVariable(name="Pc_File", default="Default")

    jog_x: AsyncMutator[float] = OpcuaVariable(name="Pc_JogX", default=0)
    jog_y: AsyncMutator[float] = OpcuaVariable(name="Pc_JogY", default=0)
    jog_z: AsyncMutator[float] = OpcuaVariable(name="Pc_JogZ", default=0)

    ready: AsyncMutator[bool] = OpcuaVariable(name="Pf_Ready", default=False)
    end: AsyncMutator[bool] = OpcuaVariable(name="Pf_End", default=True)

    current_state: AsyncMutator[str] = OpcuaVariable(name="Pd_State", default="Error")

    bed_current_temperature: AsyncMutator[float] = OpcuaVariable(
        name="Pd_tBedReal", default=0
    )
    bed_target_temperature: AsyncMutator[float] = OpcuaVariable(
        name="Pd_tBedTarget", default=0
    )

    nozzle_current_temperature: AsyncMutator[float] = OpcuaVariable(
        name="Pd_tNozReal", default=0
    )
    nozzle_target_temperature: AsyncMutator[float] = OpcuaVariable(
        name="Pd_tNozTarget", default=0
    )

    job_file: AsyncMutator[str] = OpcuaVariable(name="Pd_JobFile", default="Default")
    job_progress: AsyncMutator[float] = OpcuaVariable(name="Pd_JobProgress", default=0)
    job_time: AsyncMutator[float] = OpcuaVariable(name="Pd_JobTime", default=0)
    job_time_left: AsyncMutator[float] = OpcuaVariable(name="Pd_JobTimeLeft", default=0)
    job_time_estimate: AsyncMutator[float] = OpcuaVariable(
        name="Pd_JobTimeEst", default=0
    )

    api_resp: AsyncMutator[str] = OpcuaVariable(name="Pd_APIResp", default="default")
