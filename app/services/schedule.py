from __future__ import annotations

from datetime import datetime
from typing import List

from croniter import croniter
from croniter.croniter import CroniterBadCronError, CroniterBadDateError


def compute_next_runs(schedule: str, *, start: datetime, count: int = 3) -> List[datetime]:
    """
    Berechnet die nächsten `count` Ausführungszeitpunkte aus einer Cron-Expression.

    Aktuell: Fokus auf 5-Feld Cron (min hour dom mon dow).
    Bei Fehlern -> [] (später mit sauberer Fehlerbehandlung).
    """
    try:
        it = croniter(schedule, start)
        return [it.get_next(datetime) for _ in range(count)]
    except (CroniterBadCronError, CroniterBadDateError, ValueError):
        return []
