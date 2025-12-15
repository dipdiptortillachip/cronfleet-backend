from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import getpass
import logging
import os
import subprocess

from app.models import CronJob
from app.services.cron_parsing import parse_system_cron_line, parse_user_cron_line
from app.services.schedule import compute_next_runs

logger = logging.getLogger(__name__)

# Verhindert, dass die gleiche sudo-Warnung bei jedem Request gespammt wird
_WARNED_ROOT_SUDO_FAILED = False


def _run_command(cmd: list[str]) -> tuple[int, str, str]:
    """
    Führt einen Command aus und liefert (returncode, stdout, stderr).
    Wirft keine Exception bei non-zero Exit Codes.
    """
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError:
        logger.warning("command not found: %s", cmd[0])
        return 127, "", f"command not found: {cmd[0]}"


class LocalCronReader:
    """
    Liest Cronjobs vom lokalen System.

    Milestone 2 (lokal):
    - Dummy-Daten
    - /etc/cron.hourly (Schedule wird nach Möglichkeit aus run-parts Einträgen abgeleitet)
    - /etc/crontab
    - /etc/cron.d/*
    - User-Crontab des aktuellen Users (crontab -l)
    - Optional: Root-Crontab (sudo -n crontab -l) via Env-Flag

    Anzeige/Dedup:
    - run-parts Aggregatoren (z.B. cron.d/0hourly) blende ich standardmäßig aus,
      weil die Einzel-Skripte aus /etc/cron.hourly bereits explizit aufgelistet werden.
    - Mit CRONFLEET_INCLUDE_RUN_PARTS=1 können Aggregatoren wieder eingeblendet werden.

    Milestone 3 (Qualität):
    - deterministische Sortierung der Ausgabe
    - robustes Fehlerverhalten: keine API-Crashes, klare Warnings
    """

    def _job_sort_key(self, job: CronJob) -> tuple[str, str, str, str, str, str]:
        """
        Deterministische Sortierung für die API-Ausgabe.
        Das macht Smoke-Checks und spätere Tests/Diffs reproduzierbar.
        """
        return (
            (job.system or ""),
            (job.source or ""),
            (job.user or ""),
            (job.schedule or ""),
            (job.command or ""),
            (job.id or ""),
        )

    def _is_ignorable_line(self, line: str) -> bool:
        """
        True, wenn eine Zeile typischerweise kein Cronjob ist (und deshalb ohne Warning ignoriert werden darf):
        - leer
        - Kommentar (#)
        - ENV-Assignment (z.B. PATH=/usr/bin)
        """
        s = line.strip()
        if not s:
            return True
        if s.startswith("#"):
            return True

        # ENV-Assignments: in /etc/crontab und user crontab erlaubt
        # Typisch: "SHELL=/bin/sh", "PATH=/usr/bin:/bin"
        first = s.split()[0]
        if "=" in first and not first.startswith("@"):
            return True

        return False

    def _safe_next_runs(self, schedule: str, now: datetime, context: str) -> List[datetime]:
        """
        Berechnet next_runs robust:
        - Bei Fehler: Warning + []
        - Bei @reboot: [] (ohne Warning, weil nicht sinnvoll berechenbar)
        """
        s = (schedule or "").strip()
        if s == "@reboot":
            return []

        try:
            runs = compute_next_runs(s, start=now, count=3)
        except Exception as e:
            logger.warning("failed to compute next_runs for %s (schedule=%r): %s", context, s, e)
            return []

        # Wenn compute_next_runs intern schon "[]" zurückgibt, logge ich das als Hinweis
        # (außer @reboot, das ist oben schon abgefangen).
        if s and not runs:
            logger.warning("no next_runs computed for %s (schedule=%r)", context, s)

        return runs

    def _is_run_parts_for_dir(self, command: str, target_dir: str) -> bool:
        c = command.strip()
        return ("run-parts" in c) and (target_dir in c)

    def _infer_schedule_from_run_parts(self, target_dir: str) -> Tuple[str, str]:
        """
        Versucht eine Schedule für ein cron.* Verzeichnis (z.B. /etc/cron.hourly) zu finden,
        indem System-Cron-Quellen nach einem 'run-parts <target_dir>' Eintrag durchsucht werden.

        Rückgabe: (schedule, where)
          - schedule: Cron-Expression (oder Special)
          - where: Fundstelle wie "/etc/cron.d/0hourly:5" oder "default"
        """
        # 1) /etc/cron.d/*
        cron_d_dir = Path("/etc/cron.d")
        if cron_d_dir.is_dir():
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
                    if self._is_run_parts_for_dir(parsed.command, target_dir):
                        return parsed.schedule, f"/etc/cron.d/{file.name}:{lineno}"

        # 2) /etc/crontab
        path = Path("/etc/crontab")
        if path.is_file():
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                lines = []

            for lineno, line in enumerate(lines, start=1):
                parsed = parse_system_cron_line(line)
                if not parsed:
                    continue
                if self._is_run_parts_for_dir(parsed.command, target_dir):
                    return parsed.schedule, f"/etc/crontab:{lineno}"

        # Fallback
        return "0 * * * *", "default"

    def _get_current_user_crontab_jobs(self, now: datetime) -> List[CronJob]:
        username = getpass.getuser()
        rc, out, err = _run_command(["crontab", "-l"])

        # Kein crontab ist ok -> einfach leer zurück
        if rc != 0:
            msg = (err or out).lower()
            if rc == 127 or "no crontab for" in msg:
                return []
            logger.warning("crontab -l failed (rc=%s): %s", rc, (err or out).strip())
            return []

        jobs: List[CronJob] = []

        for lineno, line in enumerate(out.splitlines(), start=1):
            parsed = parse_user_cron_line(line)
            if not parsed:
                if not self._is_ignorable_line(line):
                    logger.warning("failed to parse user crontab line: %s:%s: %s", username, lineno, line.strip())
                continue

            job_id = f"user-crontab:{username}:{lineno}"
            jobs.append(
                CronJob(
                    id=job_id,
                    system="localhost",
                    user=username,
                    schedule=parsed.schedule,
                    command=parsed.command,
                    next_runs=self._safe_next_runs(parsed.schedule, now=now, context=job_id),
                    source="user-crontab",
                    description="Quelle: user crontab (crontab -l)",
                )
            )

        return jobs

    def _get_root_crontab_jobs(self, now: datetime) -> List[CronJob]:
        """
        Optional: root crontab via `sudo -n crontab -l`.
        -n sorgt dafür, dass sudo NICHT nach einem Passwort fragt (API bleibt responsiv).
        """
        global _WARNED_ROOT_SUDO_FAILED

        rc, out, err = _run_command(["sudo", "-n", "crontab", "-l"])

        if rc != 0:
            msg = (err or out).lower()
            if "no crontab for" in msg:
                return []

            if not _WARNED_ROOT_SUDO_FAILED:
                logger.warning(
                    "sudo -n crontab -l failed (rc=%s): %s",
                    rc,
                    (err or out).strip(),
                )
                _WARNED_ROOT_SUDO_FAILED = True
            return []

        jobs: List[CronJob] = []

        for lineno, line in enumerate(out.splitlines(), start=1):
            parsed = parse_user_cron_line(line)
            if not parsed:
                if not self._is_ignorable_line(line):
                    logger.warning("failed to parse root crontab line: root:%s: %s", lineno, line.strip())
                continue

            job_id = f"user-crontab:root:{lineno}"
            jobs.append(
                CronJob(
                    id=job_id,
                    system="localhost",
                    user="root",
                    schedule=parsed.schedule,
                    command=parsed.command,
                    next_runs=self._safe_next_runs(parsed.schedule, now=now, context=job_id),
                    source="root-crontab",
                    description="Quelle: root user crontab (sudo -n crontab -l)",
                )
            )

        return jobs

    def _should_hide_run_parts_aggregator(self, command: str) -> bool:
        """
        Blendet run-parts Aggregatoren aus (z.B. '01 * * * * run-parts /etc/cron.hourly'),
        weil die Einzeljobs aus den cron.* Verzeichnissen separat gelistet werden.

        Mit CRONFLEET_INCLUDE_RUN_PARTS=1 bleibt alles sichtbar.
        """
        if os.getenv("CRONFLEET_INCLUDE_RUN_PARTS", "0") == "1":
            return False

        if "run-parts" not in command:
            return False

        targets = ("/etc/cron.hourly", "/etc/cron.daily", "/etc/cron.weekly", "/etc/cron.monthly")
        return any(t in command for t in targets)

    def get_cron_jobs(self) -> List[CronJob]:
        now = datetime.now()
        current_user = getpass.getuser()

        jobs: List[CronJob] = [
            CronJob(
                id="local-root-system-update",
                system="localhost",
                user="root",
                schedule="0 3 * * *",
                command="/usr/bin/pacman -Syu --noconfirm",
                next_runs=self._safe_next_runs("0 3 * * *", now=now, context="dummy:local-root-system-update"),
                source="dummy",
                description="Beispiel: nächtliches System-Update (Dummy-Daten).",
            ),
            CronJob(
                id="local-user-backup-home",
                system="localhost",
                user=current_user,
                schedule="30 2 * * 1-5",
                command=f"/home/{current_user}/bin/backup-home.sh",
                next_runs=self._safe_next_runs("30 2 * * 1-5", now=now, context="dummy:local-user-backup-home"),
                source="dummy",
                description="Beispiel: User-Backup des Home-Verzeichnisses (Dummy-Daten).",
            ),
        ]

        # User crontab (aktueller User)
        jobs.extend(self._get_current_user_crontab_jobs(now=now))

        # Optional: root crontab (opt-in)
        if os.getenv("CRONFLEET_INCLUDE_ROOT_CRONTAB", "0") == "1":
            jobs.extend(self._get_root_crontab_jobs(now=now))

        # Lokale Quellen
        jobs.extend(self._read_cron_hourly_jobs(now=now))
        jobs.extend(self._read_etc_crontab_jobs(now=now))
        jobs.extend(self._read_cron_d_jobs(now=now))

        # Dedup/Anzeige: run-parts Aggregatoren standardmäßig ausblenden
        jobs = [j for j in jobs if not self._should_hide_run_parts_aggregator(j.command)]

        # Milestone 3: deterministische Reihenfolge für /crons/local
        jobs.sort(key=self._job_sort_key)

        return jobs

    def _read_cron_hourly_jobs(self, now: datetime) -> List[CronJob]:
        """
        Liest Skripte aus /etc/cron.hourly und mappt sie auf CronJob-Objekte.

        Schedule:
        - Wenn ein run-parts Eintrag für /etc/cron.hourly gefunden wird, übernehme ich dessen Schedule.
        - Sonst Fallback: "0 * * * *"
        """
        cron_hourly_dir = Path("/etc/cron.hourly")
        if not cron_hourly_dir.is_dir():
            return []

        inferred_schedule, inferred_where = self._infer_schedule_from_run_parts("/etc/cron.hourly")
        jobs: List[CronJob] = []

        for entry in cron_hourly_dir.iterdir():
            if not entry.is_file():
                continue
            if not os.access(entry, os.X_OK):
                continue

            name = entry.name

            if inferred_where == "default":
                desc = "Quelle: /etc/cron.hourly (Schedule aktuell Annahme: stündlich)."
            else:
                desc = f"Quelle: /etc/cron.hourly (Schedule abgeleitet aus run-parts: {inferred_where})."

            job_id = f"cron.hourly-{name}"
            jobs.append(
                CronJob(
                    id=job_id,
                    system="localhost",
                    user="root",
                    schedule=inferred_schedule,
                    command=str(entry),
                    next_runs=self._safe_next_runs(inferred_schedule, now=now, context=f"/etc/cron.hourly/{name}"),
                    source="/etc/cron.hourly",
                    description=desc,
                )
            )

        return jobs

    def _read_etc_crontab_jobs(self, now: datetime) -> List[CronJob]:
        path = Path("/etc/crontab")
        if not path.is_file():
            return []

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            logger.warning("failed to read /etc/crontab: %s", e)
            return []

        jobs: List[CronJob] = []

        for lineno, line in enumerate(lines, start=1):
            parsed = parse_system_cron_line(line)
            if not parsed:
                if not self._is_ignorable_line(line):
                    logger.warning("failed to parse system crontab line: /etc/crontab:%s: %s", lineno, line.strip())
                continue

            job_id = f"etc-crontab:{lineno}"
            jobs.append(
                CronJob(
                    id=job_id,
                    system="localhost",
                    user=parsed.user,
                    schedule=parsed.schedule,
                    command=parsed.command,
                    next_runs=self._safe_next_runs(parsed.schedule, now=now, context=f"/etc/crontab:{lineno}"),
                    source="/etc/crontab",
                    description="Quelle: /etc/crontab",
                )
            )

        return jobs

    def _read_cron_d_jobs(self, now: datetime) -> List[CronJob]:
        cron_d_dir = Path("/etc/cron.d")
        if not cron_d_dir.is_dir():
            return []

        jobs: List[CronJob] = []

        for file in sorted(cron_d_dir.iterdir()):
            if not file.is_file():
                continue

            try:
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError as e:
                logger.warning("failed to read %s: %s", file, e)
                continue

            for lineno, line in enumerate(lines, start=1):
                parsed = parse_system_cron_line(line)
                if not parsed:
                    if not self._is_ignorable_line(line):
                        logger.warning(
                            "failed to parse system cron.d line: /etc/cron.d/%s:%s: %s",
                            file.name,
                            lineno,
                            line.strip(),
                        )
                    continue

                job_id = f"cron.d:{file.name}:{lineno}"
                jobs.append(
                    CronJob(
                        id=job_id,
                        system="localhost",
                        user=parsed.user,
                        schedule=parsed.schedule,
                        command=parsed.command,
                        next_runs=self._safe_next_runs(parsed.schedule, now=now, context=f"/etc/cron.d/{file.name}:{lineno}"),
                        source=f"/etc/cron.d/{file.name}",
                        description=f"Quelle: /etc/cron.d/{file.name}",
                    )
                )

        return jobs


def get_local_cron_jobs() -> List[CronJob]:
    reader = LocalCronReader()
    return reader.get_cron_jobs()

