from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.models.schemas.booking import BookingCreateRequest, BookingResponse, BookingListResponse
from app.services import booking_engine, audit_service
from app.repositories import booking_repo

router = APIRouter(tags=["Bookings"])

@router.post("/bookings", status_code=201)
async def create_booking_endpoint(
    request: BookingCreateRequest,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("devotee")),
):
    """Create a new booking."""
    result = await booking_engine.create_booking(conn, UUID(current_user.id), request)
    
    background_tasks.add_task(
        audit_service.write_log,
        "booking.created",
        booking_id=str(result.booking_id),
        user_id=current_user.id
    )
    
    return result

@router.get("/bookings", response_model=BookingListResponse)
async def list_user_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("devotee")),
):
    """List bookings for the logged-in user."""
    bookings = await booking_repo.get_user_bookings(conn, UUID(current_user.id), page, limit)
    
    for b in bookings:
        b["persons"] = []
        b["service_name"] = b.get("service_name", "Unknown")
        
    return BookingListResponse(
        bookings=bookings,
        total=len(bookings),
        page=page,
        limit=limit
    )

@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking_status(
    booking_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("devotee")),
):
    """Get full details of a specific booking."""
    booking = await booking_repo.get_booking(conn, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if str(booking["user_id"]) != current_user.id and current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")
        
    return booking
