# CronFleet Backend

Minimaler FastAPI-Backend-Prototyp für CronFleet.

Ziel des Projekts:
- Übersicht über Cronjobs auf lokalen und später remote Linux-Systemen.
- Erste Phase: Nur Backend/API (kein Frontend).

---

## Aktueller Stand (Milestone 2 – in Arbeit)

- FastAPI-Anwendung mit einfachem Health-Check:
  - `GET /health` → `{"status": "ok"}`

- Datenmodell `CronJob` implementiert (Pydantic).
- Service-Schicht mit `LocalCronReader` eingeführt.
- Endpoint `GET /crons/local` verfügbar:
  - liefert aktuell eine Mischung aus:
    - statischen Dummy-Cronjobs (für frühe Entwicklung)
    - echten Cronjobs aus `/etc/cron.hourly` (z. B. `snapper`)
  - weitere lokale Quellen folgen in den nächsten Schritten:
    - `/etc/crontab`
    - `/etc/cron.d/*`
    - User-Crontabs per `crontab -l`

- Virtuelle Umgebung + Requirements-Datei vorhanden.
- Lokale Entwicklung vollständig lauffähig.

---

## Voraussetzungen

- Python 3 (empfohlen: 3.11+)
- Virtuelle Umgebung empfohlen (`python -m venv .venv`)
- Linux-System (für echte Cronjob-Daten)

---

## Installation & Start (Entwicklung)

### Mit bash/zsh

```bash
# Achtung: nur in bash/zsh, nicht in fish
cd ~/projects/cronfleet-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

### Mit fish

``` bash
cd ~/projects/cronfleet-backend
python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt

uvicorn app.main:app --reload
```

### Aufruf der API

Nach dem Start ist die API erreichbar unter:
- Swagger UI → http://127.0.0.1:8000/docs
- Health-Check → http://127.0.0.1:8000/health
- Lokale Cronjobs → http://127.0.0.1:8000/crons/local
