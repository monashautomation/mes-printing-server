import logging

import uvicorn

from .main import app
from setting import app_settings


def run() -> None:
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=app_settings.logging_level,
    )
    logging.getLogger("httpx").setLevel("WARNING")
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False, workers=1)
