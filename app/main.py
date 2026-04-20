from fastapi import FastAPI

from app.api.routes.payments import router as payments_router

app = FastAPI(title="Async Payments Service", version="1.0.0")
app.include_router(payments_router)


@app.get("/healthz")
async def healthcheck() -> dict:
    return {"status": "ok"}
