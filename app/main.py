import logging
from typing import List

from fastapi import FastAPI

from app.models import CronJob
from app.services.local_cron_reader import get_local_cron_jobs

# Simple logging setup (sichtbar in uvicorn-Konsole)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="CronFleet API",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/crons/local", response_model=List[CronJob])
async def list_local_crons():
    return get_local_cron_jobs()

