import logging

import uvicorn

from app.dependencies import ctx
from app.main import app


def run():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=ctx.settings.logging_level,
    )
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False, workers=1)
