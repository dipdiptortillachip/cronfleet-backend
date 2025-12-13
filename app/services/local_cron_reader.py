from datetime import datetime
from pathlib import Path
from typing import List

import os

from app.models import CronJob
from app.services.cron_parsing import parse_system_cron_line
from app.services.schedule import compute_next_runs


class LocalCronReader:
    """
    Liest Cronjobs vom lokalen System.

    Milestone 2 – Phase: Mischung aus Dummy + echten Daten
    - Gibt weiterhin statische Beispiel-Daten zurück.
    - Liest zusätzlich Skripte aus /etc/cron.hourly und mappt sie auf CronJob.
    - Liest zusätzlich /etc/crontab (systemweite Cronjobs).

    Später:
    - Wird echte Crontabs auslesen, z.B.:
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
                next_runs=compute_next_runs("0 3 * * *", start=now, count=3),
                description="Beispiel: nächtliches System-Update (Dummy-Daten).",
            ),
            CronJob(
                id="local-user-backup-home",
                system="localhost",
                user="tortillachip",
                schedule="30 2 * * 1-5",
                command="/home/tortillachip/bin/backup-home.sh",
                next_runs=compute_next_runs("30 2 * * 1-5", start=now, count=3),
                description="Beispiel: User-Backup des Home-Verzeichnisses (Dummy-Daten).",
            ),
        ]

        # Echte Daten aus /etc/cron.hourly ergänzen (falls vorhanden)
        jobs.extend(self._read_cron_hourly_jobs(now=now))

        # Echte Daten aus /etc/crontab ergänzen (falls vorhanden)
        jobs.extend(self._read_etc_crontab_jobs(now=now))

        # Echte Daten aus /etc/cron.d/* ergänzen (falls vorhanden)
        jobs.extend(self._read_cron_d_jobs(now=now))
        
        return jobs

    def _read_cron_hourly_jobs(self, now: datetime) -> List[CronJob]:
        """
        Liest Skripte aus /etc/cron.hourly und mappt sie auf CronJob-Objekte.

        Annahmen:
        - User: root (typischerweise System-Jobs).
        - Schedule: "0 * * * *" (stündlich) als erste grobe Annahme.
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
                    next_runs=compute_next_runs("0 * * * *", start=now, count=3),
                    description="Quelle: /etc/cron.hourly (Schedule aktuell pauschal: stündlich).",
                )
            )

        return jobs

    def _read_etc_crontab_jobs(self, now: datetime) -> List[CronJob]:
        """
        Liest /etc/crontab und mappt Zeilen auf CronJob.

        System-crontab enthält üblicherweise ein zusätzliches 'user'-Feld.
        ENV-Zeilen und Kommentare werden ignoriert.
        """
        path = Path("/etc/crontab")
        if not path.is_file():
            return []

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []

        jobs: List[CronJob] = []

        for lineno, line in enumerate(lines, start=1):
            parsed = parse_system_cron_line(line)
            if not parsed:
                continue

            jobs.append(
                CronJob(
                    id=f"etc-crontab:{lineno}",
                    system="localhost",
                    user=parsed.user,
                    schedule=parsed.schedule,
                    command=parsed.command,
                    next_runs=compute_next_runs(parsed.schedule, start=now, count=3),
                    description="Quelle: /etc/crontab",
                )
            )

        return jobs

    def _read_cron_d_jobs(self, now: datetime) -> List[CronJob]:
        """
        Liest /etc/cron.d/* und mappt Zeilen auf CronJob.

        Format ist wie /etc/crontab: m h dom mon dow user command...
        Kommentare/ENV werden vom Parser ignoriert.
        """
        cron_d_dir = Path("/etc/cron.d")
        if not cron_d_dir.is_dir():
            return []

        jobs: List[CronJob] = []

        for file in sorted(cron_d_dir.iterdir()):
            if not file.is_file():
                continue

            try:
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue

            for lineno, line in enumerate(lines, start=1):
                parsed = parse_system_cron_line(line)
                if not parsed:
                    continue

                jobs.append(
                    CronJob(
                        id=f"cron.d:{file.name}:{lineno}",
                        system="localhost",
                        user=parsed.user,
                        schedule=parsed.schedule,
                        command=parsed.command,
                        next_runs=compute_next_runs(parsed.schedule, start=now, count=3),
                        description=f"Quelle: /etc/cron.d/{file.name}",
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
