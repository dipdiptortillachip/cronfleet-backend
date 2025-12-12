from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CronJob(BaseModel):
    """
    Repräsentiert einen einzelnen Cronjob auf einem System.

    Dieses Modell ist bewusst generisch gehalten und wird sowohl
    für lokale als auch für spätere Remote-Systeme verwendbar sein.
    """

    id: str
    system: str
    user: str
    schedule: str
    command: str
    next_runs: List[datetime]
    description: Optional[str] = None

