import pytest


@pytest.mark.asyncio
async def test_delete_printed_file(printer1_after_printing):
    printer = await printer1_after_printing

    file_path = printer.job.job_file

    await printer.delete_printed_file(file_path)

    assert file_path not in printer.uploaded_files
