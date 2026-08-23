from fastapi import FastAPI

from app.routers import auth, contracts, obligations

app = FastAPI(
    title="SLA / Contract Obligation Monitor",
    description="Tracks contract obligations and deadlines, alerts before breaches happen.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(obligations.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "sla-monitor-api"}


@app.get("/health")
def health():
    return {"status": "healthy"}
