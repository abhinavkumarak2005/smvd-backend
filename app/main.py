import logging
import uuid
import time

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database import init_db, close_db, check_db_health

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Settings ─────────────────────────────────────────────────────────────────
settings = get_settings()

# ── Sentry (optional) ────────────────────────────────────────────────────────
if settings.SENTRY_DSN and settings.SENTRY_DSN.startswith("https://"):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2,
    )
    logger.info("Sentry initialized.")

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# ── APScheduler ──────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
# Background jobs registered here in Day 8:
# scheduler.add_job(slot_cleanup.cleanup_expired_bookings, "interval", minutes=5)
# scheduler.add_job(notice_scheduler.update_notice_statuses, "interval", minutes=5)

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sri Manakula Vinayagar Devasthanam API",
    version="1.0.0",
    description="Temple booking and operations platform for SMVD",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Rate limit error handler ──────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware ───────────────────────────────────────────────────────────
allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Logging Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.info(
        f"request_id={request_id} method={request.method} "
        f"path={request.url.path} status={response.status_code} "
        f"duration={duration_ms}ms ip={request.client.host if request.client else 'unknown'}"
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── Startup & Shutdown Events ─────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info(f"Starting SMVD API — environment: {settings.ENVIRONMENT}")
    await init_db()
    scheduler.start()
    logger.info("APScheduler started.")


@app.on_event("shutdown")
async def shutdown():
    await close_db()
    scheduler.shutdown()
    logger.info("SMVD API shut down cleanly.")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    db_status = "connected" if await check_db_health() else "disconnected"
    return JSONResponse(
        content={
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "db": db_status,
            "version": "1.0.0",
        }
    )
