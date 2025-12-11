# CronFleet Backend

Minimaler FastAPI-Backend-Prototyp für CronFleet.

Ziel des Projekts:
- Übersicht über Cronjobs auf lokalen und später remote Linux-Systemen.
- Erste Phase: Nur Backend/API (kein Frontend).

## Aktueller Stand

- FastAPI-Anwendung mit einfachem Health-Check:
  - `GET /health` → `{"status": "ok"}`

## Voraussetzungen

- Python 3 (z.B. 3.11+)
- Virtuelle Umgebung empfohlen (`python -m venv .venv`)

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

``` fish
cd ~/projects/cronfleet-backend
python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Die API ist dann erreichbar unter:
Swagger UI: http://127.0.0.1:8000/docs
Health-Check: http://127.0.0.1:8000/health
