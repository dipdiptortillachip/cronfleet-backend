from datetime import datetime, timedelta
from typing import List

from app.models import CronJob


class LocalCronReader:
    """
    Liest Cronjobs vom lokalen System.

    Milestone 2 – Phase Dummy:
    - Gibt nur statische Beispiel-Daten zurück.
    - Dient dazu, die Service-Schicht vorzubereiten.

    Später:
    - Wird die echten Crontabs auslesen, z.B.:
      - /etc/crontab
      - /etc/cron.d/*
      - User-Crontabs (crontab -l -u <user>)
    """

    def get_cron_jobs(self) -> List[CronJob]:
        now = datetime.now()

        return [
            CronJob(
                id="local-root-system-update",
                system="localhost",
                user="root",
                schedule="0 3 * * *",
                command="/usr/bin/pacman -Syu --noconfirm",
                next_runs=[now + timedelta(days=i) for i in range(1, 4)],
                description="Beispiel: nächtliches System-Update (Dummy-Daten).",
            ),
            CronJob(
                id="local-user-backup-home",
                system="localhost",
                user="tortillachip",
                schedule="30 2 * * 1-5",
                command="/home/tortillachip/bin/backup-home.sh",
                next_runs=[now + timedelta(days=i) for i in range(2, 5)],
                description="Beispiel: User-Backup des Home-Verzeichnisses (Dummy-Daten).",
            ),
        ]


def get_local_cron_jobs() -> List[CronJob]:
    """
    Convenience-Funktion für den API-Layer.

    Nutzt intern den LocalCronReader, um die Cronjobs zu holen.
    """
    reader = LocalCronReader()
    return reader.get_cron_jobs()

