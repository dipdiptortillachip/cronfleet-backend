from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import os

from app.models import CronJob


class LocalCronReader:
    """
    Liest Cronjobs vom lokalen System.

    Milestone 2 – Phase: Mischung aus Dummy + echten Daten
    - Gibt weiterhin statische Beispiel-Daten zurück.
    - Liest zusätzlich Skripte aus /etc/cron.hourly und mappt sie auf CronJob.

    Später:
    - Wird die echten Crontabs auslesen, z.B.:
      - /etc/crontab (falls vorhanden)
      - /etc/cron.d/*
      - User-Crontabs (crontab -l -u <user>)
      - ggf. systemd-Timer-Infos
    """

    def get_cron_jobs(self) -> List[CronJob]:
        now = datetime.now()

        jobs: List[CronJob] = [
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

        # Echte Daten aus /etc/cron.hourly ergänzen (falls vorhanden)
        jobs.extend(self._read_cron_hourly_jobs(now=now))

        return jobs

    def _read_cron_hourly_jobs(self, now: datetime) -> List[CronJob]:
        """
        Liest Skripte aus /etc/cron.hourly und mappt sie auf CronJob-Objekte.

        Annahmen:
        - User: root (typischerweise System-Jobs).
        - Schedule: "0 * * * *" (stündlich) als erste grobe Annahme.
          Später können wir das genauer modellieren (z.B. anhand systemd-Timer).
        """
        cron_hourly_dir = Path("/etc/cron.hourly")

        if not cron_hourly_dir.is_dir():
            return []

        jobs: List[CronJob] = []

        for entry in cron_hourly_dir.iterdir():
            if not entry.is_file():
                continue

            # Nur ausführbare Skripte berücksichtigen
            if not os.access(entry, os.X_OK):
                continue

            name = entry.name

            jobs.append(
                CronJob(
                    id=f"cron.hourly-{name}",
                    system="localhost",
                    user="root",
                    schedule="0 * * * *",  # Annahme: stündlich
                    command=str(entry),
                    next_runs=[now + timedelta(hours=i) for i in range(1, 4)],
                    description=(
                        "Abgeleitet aus /etc/cron.hourly (Dummy-Schedule: stündlich)."
                    ),
                )
            )

        return jobs


def get_local_cron_jobs() -> List[CronJob]:
    """
    Convenience-Funktion für den API-Layer.

    Nutzt intern den LocalCronReader, um die Cronjobs zu holen.
    """
    reader = LocalCronReader()
    return reader.get_cron_jobs()

