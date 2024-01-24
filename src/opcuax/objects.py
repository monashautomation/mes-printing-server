from opcuax.core import OpcuaObject, OpcuaVariable


class OpcuaPrinter(OpcuaObject):
    program_id = OpcuaVariable(name="progID", default=0)
    start = OpcuaVariable(name="start", default=False)

    part_removed = OpcuaVariable(name="Pc_PartRemoved", default=False)
    bed_cleaned = OpcuaVariable(name="Pc_BedCleaned", default=False)

    file = OpcuaVariable(name="Pc_File", default="Default")

    jog_x = OpcuaVariable(name="Pc_JogX", default=0)
    jog_y = OpcuaVariable(name="Pc_JogY", default=0)
    jog_z = OpcuaVariable(name="Pc_JogZ", default=0)

    ready = OpcuaVariable(name="Pf_Ready", default=False)
    end = OpcuaVariable(name="Pf_End", default=True)

    current_state = OpcuaVariable(name="Pd_State", default="Error")

    bed_current_temperature = OpcuaVariable(name="Pd_tBedReal", default=0)
    bed_target_temperature = OpcuaVariable(name="Pd_tBedTarget", default=0)

    nozzle_current_temperature = OpcuaVariable(name="Pd_tNozReal", default=0)
    nozzle_target_temperature = OpcuaVariable(name="Pd_tNozTarget", default=0)

    job_file = OpcuaVariable(name="Pd_JobFile", default="Default")
    job_progress = OpcuaVariable(name="Pd_JobProgress", default=0)
    job_time = OpcuaVariable(name="Pd_JobTime", default=0)
    job_time_left = OpcuaVariable(name="Pd_JobTimeLeft", default=0)
    job_time_estimate = OpcuaVariable(name="Pd_JobTimeEst", default=0)

    api_resp = OpcuaVariable(name="Pd_APIResp", default="default")
