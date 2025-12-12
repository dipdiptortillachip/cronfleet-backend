from typing import List

from fastapi import FastAPI

from app.models import CronJob
from app.services.local_cron_reader import get_local_cron_jobs

app = FastAPI(
    title="CronFleet API",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """
    Einfacher Health-Check-Endpoint.
    Wird später um Status-Infos erweitert werden.
    """
    return {"status": "ok"}


@app.get("/crons/local", response_model=List[CronJob])
async def list_local_crons():
    """
    Liefert lokale Cronjobs.

    Aktuell:
    - Gibt nur statische Dummy-Daten zurück.
    - Dient als erste Implementierung von Milestone 2 (Phase: Dummy-Reader).

    Später:
    - Wird auf einen echten LocalCronReader umgestellt, der
      /etc/crontab, /etc/cron.d/* und User-Crontabs ausliest.
    """
    return get_local_cron_jobs()

