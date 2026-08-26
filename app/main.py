from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.routers import auth, contracts, obligations, monitoring
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background APScheduler for deadline checks & alerts
    start_scheduler()
    yield
    # Shutdown: Stop background scheduler cleanly
    stop_scheduler()


app = FastAPI(
    title="SLA / Contract Obligation Monitor",
    description="Tracks contract obligations and deadlines, alerts before breaches happen.",
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(obligations.router)
app.include_router(monitoring.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "sla-monitor-api"}


@app.get("/health")
def health():
    return {"status": "healthy"}
