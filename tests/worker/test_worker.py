import pytest

from db.models import Order
from worker import WorkerEvent, WorkerState, PrinterWorker


def test_all_events_have_handlers():
    assert all(e in PrinterWorker.event_handlers for e in WorkerEvent)


def test_all_states_have_handlers():
    assert all(e in PrinterWorker.state_handlers for e in WorkerState)


async def test_initial_state(idle_worker):
    assert idle_worker.state == WorkerState.Connecting


async def test_initial_to_connected(idle_worker):
    worker = idle_worker
    await worker.work()

    assert worker.state == WorkerState.Connected


async def test_connected_to_ready(idle_worker):
    worker = idle_worker
    await worker.work()
    await worker.work()

    assert worker.state == WorkerState.Ready


async def test_ready_to_heating(idle_worker, admin_approved_order):
    worker = idle_worker

    for _ in range(3):
        await worker.work()

    assert worker.state == WorkerState.Heating
    assert worker.current_order.id == admin_approved_order.id
    assert worker.current_order.print_start_time is not None


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


async def test_printed_to_wait_pickup(printed_worker, admin_approved_order):
    worker = printed_worker

    worker.octo.tick()
    await worker.work()

    assert not worker.octo.uploaded_files
    assert worker.state == WorkerState.WaitingForPickup

    job_file = await worker.opcua_printer.job_file.get()
    job_progress = await worker.opcua_printer.job_progress.get()
    order = await worker.session.get(Order, admin_approved_order.id)

    assert job_file == ""
    assert job_progress == 0
    assert order.print_end_time is not None
    assert worker.current_order is None

    assert worker.octo.head_xyz != [0, 0, 0]


async def test_during_waiting_for_pickup(waiting_worker):
    worker = waiting_worker

    for _ in range(10):
        worker.octo.tick()
        await worker.work()

        assert worker.state == WorkerState.WaitingForPickup


async def test_waiting_to_picked(waiting_worker):
    worker = waiting_worker

    worker.put_event(WorkerEvent.Pick)
    worker.octo.tick()
    await worker.work()

    assert worker.state == WorkerState.Ready
