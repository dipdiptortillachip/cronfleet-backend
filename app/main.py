from fastapi import FastAPI

app = FastAPI(
    title="CronFleet API",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """
    Einfacher Health-Check-Endpoint.
    Wird später um Status-Infos erweitert werden.
    """
    return {"status": "ok"}

