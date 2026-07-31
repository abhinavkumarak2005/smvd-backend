from datetime import date
from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.services import calendar_service

router = APIRouter(tags=["Public - Availability"])

@router.get("/availability")
async def check_availability(
    target_date: date,
    service_id: UUID,
    conn: asyncpg.Connection = Depends(get_db)
):
    """Check if a specific date is available for a given service."""
    status_obj = await calendar_service.check_date(conn, target_date, service_id)
    
    if status_obj.status == "open":
        return {"available": True, "reason": None}
    else:
        return {"available": False, "reason": "BLOCKED", "notes": status_obj.notes}
