from datetime import date
from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.models.schemas.report import (
    DashboardKPIs, DailySummary, WeeklyTrend, MonthlyReport, 
    OccupancyReport, CertificateReport
)
from app.services import report_service

router = APIRouter(tags=["Admin - Reports"])

@router.get("/admin/reports/dashboard", response_model=DashboardKPIs)
async def get_dashboard(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("staff")),
):
    """Real-time admin dashboard data."""
    return await report_service.get_dashboard_kpis(conn)

@router.get("/admin/reports/daily", response_model=DailySummary)
async def get_daily_report(
    report_date: date = Query(..., alias="date"),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("staff")),
):
    """Get daily summary report."""
    return await report_service.get_daily_summary(conn, report_date)

@router.get("/admin/reports/weekly", response_model=WeeklyTrend)
async def get_weekly_report(
    start: date = Query(...),
    end: date = Query(...),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("staff")),
):
    """Get weekly trend report."""
    return await report_service.get_weekly_trend(conn, start, end)

@router.get("/admin/reports/monthly", response_model=MonthlyReport)
async def get_monthly_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("staff")),
):
    """Get monthly report."""
    return await report_service.get_monthly_report(conn, year, month)

@router.get("/admin/reports/occupancy", response_model=OccupancyReport)
async def get_occupancy_report(
    service_id: UUID = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("staff")),
):
    """Get occupancy report for a specific service."""
    return await report_service.get_service_occupancy(conn, service_id, start, end)

@router.get("/admin/reports/certificates", response_model=CertificateReport)
async def get_certificate_report(
    start: date | None = Query(None),
    end: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("staff")),
):
    """Get certificate issuance report."""
    return await report_service.get_certificate_report(conn, start, end)

@router.get("/admin/reports/audit-log")
async def get_audit_log_report(
    action: str | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    page: int = Query(1, ge=1),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get raw audit logs. Requires admin role."""
    return await report_service.get_audit_logs(conn, action, start, end, page)
