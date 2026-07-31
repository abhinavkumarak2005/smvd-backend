import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database import init_db, close_db, check_db_health
from app.middleware.rate_limit import limiter
from app.middleware.request_logging import request_logging_middleware
from app.routers.auth.otp import router as otp_router
from app.routers.auth.login import router as login_router
from app.routers.public.services import router as services_router
from app.routers.e_undiyal.donate import router as e_undiyal_router
from app.routers.e_undiyal.certificate import router as certificate_router
from app.routers.admin.certificates import router as admin_certificates_router
from app.routers.public.notices import router as public_notices_router
from app.routers.admin.notices import router as admin_notices_router
from app.routers.admin.users import router as admin_users_router
from app.routers.admin.e_undiyal import router as admin_e_undiyal_router
from app.routers.admin.bookings import router as admin_bookings_router
from app.routers.admin.services import router as admin_services_router
from app.routers.admin.inventory import router as admin_inventory_router
from app.routers.admin.reports import router as admin_reports_router
from app.routers.admin.calendar import router as admin_calendar_router
from app.routers.bookings.router import router as bookings_router
from app.routers.payments.router import router as payments_router
from app.routers.public.availability import router as public_availability_router
from app.services.notice_service import run_scheduler as notice_scheduler
from app.background.slot_cleanup import cleanup_expired_bookings

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Settings ──────────────────────────────────────────────────────────────────
settings = get_settings()

# ── Sentry (optional) ─────────────────────────────────────────────────────────
if settings.SENTRY_DSN and settings.SENTRY_DSN.startswith("https://"):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2,
    )
    logger.info("Sentry initialized.")

# ── APScheduler ───────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(notice_scheduler, "interval", minutes=5, id="notice_scheduler")
scheduler.add_job(cleanup_expired_bookings, "interval", minutes=5, id="slot_cleanup_scheduler")

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sri Manakula Vinayagar Devasthanam API",
    version="1.0.0",
    description="Temple booking and operations platform for SMVD",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Rate Limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Logging ────────────────────────────────────────────────────────────
app.middleware("http")(request_logging_middleware)

# ── Auth Routers ───────────────────────────────────────────────────────────────
app.include_router(otp_router, prefix="/api/v1/auth")
app.include_router(login_router, prefix="/api/v1/auth")
app.include_router(services_router, prefix="/api/v1")
app.include_router(e_undiyal_router, prefix="/api/v1")
app.include_router(certificate_router, prefix="/api/v1")
app.include_router(admin_certificates_router, prefix="/api/v1")
app.include_router(public_notices_router, prefix="/api/v1")
app.include_router(admin_notices_router, prefix="/api/v1")
app.include_router(admin_users_router, prefix="/api/v1")
app.include_router(admin_e_undiyal_router, prefix="/api/v1")
app.include_router(admin_bookings_router, prefix="/api/v1")
app.include_router(admin_services_router, prefix="/api/v1")
app.include_router(admin_inventory_router, prefix="/api/v1")
app.include_router(admin_reports_router, prefix="/api/v1")
app.include_router(admin_calendar_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(public_availability_router, prefix="/api/v1")


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("Starting SMVD API — environment: %s", settings.ENVIRONMENT)
    await init_db()
    scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    await close_db()
    scheduler.shutdown()
    logger.info("SMVD API shut down cleanly.")


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    db_ok = await check_db_health()
    return JSONResponse(content={
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "db": "connected" if db_ok else "disconnected",
        "version": "1.0.0",
    })
