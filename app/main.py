from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
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
    version="0.4.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - allows the deployed Streamlit frontend (a different origin in production)
# to call this API from the browser. CORS_ORIGINS is set via environment variable;
# defaults to common local dev ports so nothing breaks while developing locally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
