from datetime import datetime, timedelta
from typing import List

from app.models import CronJob


def get_local_cron_jobs() -> List[CronJob]:
    """
    Liefert eine Liste von lokalen Cronjobs.

    Aktuell:
    - Gibt nur statische Dummy-Daten zurück.
    - Dient als erste Implementierung für Milestone 2.
    - Später wird diese Funktion die echten Crontabs auslesen
      (z.B. /etc/crontab, /etc/cron.d/*, crontab -l -u user).
    """

    now = datetime.now()

    return [
        CronJob(
            id="local-root-system-update",
            system="localhost",
            user="root",
            schedule="0 3 * * *",
            command="/usr/bin/pacman -Syu --noconfirm",
            next_runs=[
                now + timedelta(days=i) for i in range(1, 4)
            ],
            description="Beispiel: nächtliches System-Update (Dummy-Daten).",
        ),
        CronJob(
            id="local-user-backup-home",
            system="localhost",
            user="tortillachip",
            schedule="30 2 * * 1-5",
            command="/home/tortillachip/bin/backup-home.sh",
            next_runs=[
                now + timedelta(days=i) for i in range(2, 5)
            ],
            description="Beispiel: User-Backup des Home-Verzeichnisses (Dummy-Daten).",
        ),
    ]

