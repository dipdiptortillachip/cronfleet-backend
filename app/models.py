from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CronJob(BaseModel):
    id: str
    system: str
    user: str
    schedule: str
    command: str
    next_runs: List[datetime]

    # Maschinenlesbar: wo kommt der Job her?
    # Beispiele: "dummy", "user-crontab", "/etc/crontab", "/etc/cron.d/0hourly", "/etc/cron.hourly"
    source: str = Field(default="unknown")

    # lesbar Debug
    description: Optional[str] = None

