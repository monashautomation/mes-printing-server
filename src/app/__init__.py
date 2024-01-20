import uvicorn

from app.main import app


def run():
    uvicorn.run(app, host="0.0.0.0", port=8000)
