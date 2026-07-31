from datetime import date
from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.models.schemas.admin import CalendarDateCreateRequest, CalendarDateResponse
from app.repositories import calendar_repo
from app.services import audit_service

router = APIRouter(tags=["Admin - Calendar"])

@router.get("/admin/calendar", response_model=list[CalendarDateResponse])
async def list_calendar_dates(
    start: date,
    end: date,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin"))
):
    """Get all configured calendar rules between start and end dates."""
    if end < start:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    return await calendar_repo.get_date_range(conn, start, end)

@router.get("/admin/calendar/{target_date}", response_model=CalendarDateResponse)
async def get_calendar_date(
    target_date: date,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin"))
):
    """Get rules for a specific date. If unconfigured, defaults to open."""
    res = await calendar_repo.get_date(conn, target_date)
    if res:
        return res
    
    # Return default 'open' representation if not explicitly configured in DB
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "date": str(target_date),
        "status": "open",
        "notes": None,
        "notes_tamil": None,
        "allowed_service_ids": []
    }

@router.post("/admin/calendar/{target_date}", response_model=CalendarDateResponse)
async def configure_calendar_date(
    target_date: date,
    request: CalendarDateCreateRequest,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin"))
):
    """Upsert calendar rules for a specific date (block or partially allow)."""
    if str(request.date) != str(target_date):
        raise HTTPException(status_code=400, detail="Path date and body date must match")
        
    if request.status == "partial" and not request.allowed_service_ids:
        raise HTTPException(status_code=400, detail="partial status requires at least one allowed_service_id")
        
    result = await calendar_repo.upsert_date(
        conn,
        target_date,
        request.status,
        request.allowed_service_ids,
        request.notes,
        request.notes_tamil,
        UUID(current_user.id)
    )
    
    background_tasks.add_task(
        audit_service.write_log,
        "calendar.date_updated",
        target_id=str(result["id"]),
        user_id=current_user.id,
        new_values={"status": request.status, "date": str(target_date)}
    )
    
    return result

@router.delete("/admin/calendar/{target_date}", status_code=204)
async def delete_calendar_date(
    target_date: date,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin"))
):
    """Delete explicit calendar rules for a date, reverting it to open."""
    record = await calendar_repo.get_date(conn, target_date)
    if not record:
        raise HTTPException(status_code=404, detail="Date not configured explicitly")
        
    await calendar_repo.delete_date(conn, target_date)
    
    background_tasks.add_task(
        audit_service.write_log,
        "calendar.date_deleted",
        target_id=str(record["id"]),
        user_id=current_user.id,
        new_values={"date": str(target_date)}
    )
