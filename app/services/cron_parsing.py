from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ParsedCronLine:
    schedule: str
    user: str
    command: str


def parse_system_cron_line(line: str) -> Optional[ParsedCronLine]:
    """
    Parser für System-Cron-Dateien wie /etc/crontab und /etc/cron.d/*.

    Unterstützt:
    - Standard-Format: m h dom mon dow user command...
    - Specials: @daily/@hourly/... (z.B. "@daily root /path/to/cmd")
      (@reboot wird zwar geparst, aber croniter kann dafür i.d.R. keine next_runs berechnen -> [])

    Ignoriert:
    - leere Zeilen, Kommentare
    - einfache ENV-Zeilen wie PATH=..., SHELL=...
    """
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    parts = raw.split()

    # ENV-Zeilen (typisch: KEY=VALUE)
    if len(parts) == 1 and "=" in parts[0]:
        return None

    # @reboot / @daily etc.: "@daily root /path/to/cmd"
    if parts[0].startswith("@"):
        if len(parts) < 3:
            return None
        schedule = parts[0]
        user = parts[1]
        command = " ".join(parts[2:])
        return ParsedCronLine(schedule=schedule, user=user, command=command)

    # Standard: 5 Felder + user + command
    if len(parts) < 7:
        return None

    schedule = " ".join(parts[0:5])
    user = parts[5]
    command = " ".join(parts[6:])
    return ParsedCronLine(schedule=schedule, user=user, command=command)

