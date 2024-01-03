import pytest

from worker import WorkerEvent, WorkerState, PrinterWorker

from octo.models import Job, File, CurrentJob, Progress


def test_all_events_have_handlers():
    assert all(e in PrinterWorker.event_handlers for e in WorkerEvent)


def test_all_states_have_handlers():
    assert all(e in PrinterWorker.state_handlers for e in WorkerState)


@pytest.mark.asyncio
async def test_initial_state(idle_worker):
    assert idle_worker.state == WorkerState.Connecting


@pytest.mark.asyncio
async def test_initial_to_connected(idle_worker):
    worker = idle_worker
    await worker.work()

    assert worker.state == WorkerState.Connected


@pytest.mark.asyncio
async def test_connected_to_ready(idle_worker):
    worker = idle_worker
    await worker.work()
    await worker.work()

    assert worker.state == WorkerState.Ready


@pytest.mark.asyncio
async def test_ready_to_heating(idle_worker, admin_approved_order):
    worker = idle_worker

    for _ in range(3):
        await worker.work()

    assert worker.state == WorkerState.Heating
    assert worker.current_order.id == admin_approved_order.id
    assert worker.current_order.print_start_time is not None


@pytest.mark.asyncio
async def test_during_heating(idle_worker):
    worker = idle_worker

    for _ in range(3):
        await worker.work()

    for i in range(worker.octo.heater.required_ticks):
        worker.octo.tick()
        await worker.work()

        temp = await worker.octo.current_temperature()
        bed_actual = await worker.opcua_printer.bed_current_temperature.get()
        nozzle_actual = await worker.opcua_printer.nozzle_current_temperature.get()

        assert temp.bed.actual == bed_actual
        assert temp.tool0.actual == nozzle_actual

        if i < worker.octo.heater.required_ticks - 1:
            assert worker.state == WorkerState.Heating

    assert worker.state == WorkerState.Printing


@pytest.mark.asyncio
async def test_printing_to_printed(printing_worker):
    worker = printing_worker

    ticks = worker.octo.job.required_ticks

    for i in range(ticks):
        worker.octo.tick()
        await worker.work()

        job_status = await worker.octo.current_job()

        job_file = await worker.opcua_printer.job_file.get()
        job_progress = await worker.opcua_printer.job_progress.get()

        assert job_file == job_status.job.file.name
        assert job_progress == job_status.progress.completion

        if i < ticks - 1:
            assert worker.state == WorkerState.Printing

    assert worker.state == WorkerState.Printed


@pytest.mark.asyncio
async def test_printed_to_wait_pickup(printed_worker, admin_approved_order):
    worker = printed_worker

    worker.octo.tick()
    await worker.work()

    assert worker.state == WorkerState.WaitingForPickup

    job_file = await worker.opcua_printer.job_file.get()
    job_progress = await worker.opcua_printer.job_progress.get()
    order = await worker.session.get_order_by_id(admin_approved_order.id)

    assert job_file == ""
    assert job_progress == 0
    assert order.print_end_time is not None
    assert worker.current_order is None

    assert worker.octo.head_xyz != [0, 0, 0]


@pytest.mark.asyncio
async def test_during_waiting_for_pickup(waiting_worker):
    worker = waiting_worker

    for _ in range(10):
        worker.octo.tick()
        await worker.work()

        assert worker.state == WorkerState.WaitingForPickup


@pytest.mark.asyncio
async def test_waiting_to_picked(waiting_worker):
    worker = waiting_worker

    worker.put_event(WorkerEvent.Pick)
    worker.octo.tick()
    await worker.work()

    assert worker.state == WorkerState.Ready


@pytest.mark.asyncio
async def test_delete_printed_file(printed_worker, mocker):
    worker = await printed_worker

    worker.state = WorkerState.Printed

    mock_delete = mocker.patch.object(worker.octo, 'delete_printed_file', autospec=True)

    # Create File obj and Job obj
    mock_file = File(
        name="test_file.gcode",
        display="test file.gcode",
        path="test_path/file.gcode",
        type="machine_code",
        type_path=["machine_code", "gcode"]
    )
    mock_job = Job(file=mock_file)

    mock_progress = Progress(
        completion=100.0,
        filepos=12345,
        printTime=3600,
        printTimeLeft=0,
        printTimeLeftOrigin="linear"
    )

    mock_current_job = CurrentJob(job=mock_job, progress=mock_progress, state='Printing', error=None)

    mocker.patch.object(worker.octo, "current_job", return_value=mock_current_job)

    await worker.work()

    mock_delete.assert_called_once_with("test_path/file.gcode")

    assert worker.state == WorkerState.WaitingForPickup
