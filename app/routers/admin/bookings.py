from datetime import date
from uuid import UUID
from pydantic import BaseModel
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.repositories import booking_repo, slot_inventory_repo
from app.services import notification_service, audit_service, payment_service

router = APIRouter(tags=["Admin - Bookings"])

class BookingApproveRequest(BaseModel):
    note: str

class BookingRejectRequest(BaseModel):
    reason: str

@router.get("/admin/bookings/pending-approvals")
async def get_pending_approvals(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get all bookings pending approval."""
    return await booking_repo.get_pending_approvals(conn)

@router.get("/admin/bookings")
async def list_bookings(
    status: str | None = Query(None),
    booking_date: date | None = Query(None, alias="date"),
    service_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """List all bookings with filters."""
    return await booking_repo.get_all_bookings(
        conn, status=status, booking_date=booking_date, 
        service_id=service_id, page=page
    )

@router.get("/admin/bookings/{booking_id}")
async def get_booking_detail(
    booking_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get full details of a specific booking."""
    booking = await booking_repo.get_booking(conn, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@router.post("/admin/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: UUID,
    body: BookingApproveRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Approve a booking."""
    booking = await booking_repo.get_booking(conn, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking["status"] != "pending_approval":
        raise HTTPException(status_code=400, detail="Booking is not pending approval")

    await booking_repo.update_status(conn, booking_id, "approved", UUID(current_user.id), body.note)
    
    # Notify user
    # Ideally fetch user phone from users table, stubbing here
    user_phone = booking.get("phone", "+919999999999") 
    verification_link = f"https://smvd.org/verify-booking/{booking_id}"
    await notification_service.send_sms(
        user_phone, 
        f"Your booking has been approved! Verify your ticket originality here: {verification_link}"
    )
    
    await audit_service.write_log("booking.approved", booking_id=str(booking_id), admin_id=str(current_user.id))
    return {"message": "Booking approved"}

@router.post("/admin/bookings/{booking_id}/reject")
async def reject_booking(
    booking_id: UUID,
    body: BookingRejectRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Reject a booking and refund if needed."""
    booking = await booking_repo.get_booking(conn, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking["status"] not in ("pending_payment", "pending_approval"):
        raise HTTPException(status_code=400, detail="Cannot reject this booking")

    await booking_repo.update_status(conn, booking_id, "rejected")
    await slot_inventory_repo.release_slot(conn, booking_id)
    
    if booking["payment"] and booking["payment"]["status"] == "success":
        await payment_service.initiate_refund(booking["payment"]["id"], booking["payment"]["amount_paise"])

    user_phone = booking.get("phone", "+919999999999") 
    await notification_service.send_sms(user_phone, f"Your booking has been rejected. Reason: {body.reason}")
    
    await audit_service.write_log("booking.rejected", booking_id=str(booking_id), admin_id=str(current_user.id))
    return {"message": "Booking rejected"}

@router.post("/admin/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: UUID,
    body: BookingRejectRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Cancel a booking."""
    booking = await booking_repo.get_booking(conn, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    await booking_repo.update_status(conn, booking_id, "cancelled")
    await slot_inventory_repo.release_slot(conn, booking_id)
    
    if booking["payment"] and booking["payment"]["status"] == "success":
        await payment_service.initiate_refund(booking["payment"]["id"], booking["payment"]["amount_paise"])

    user_phone = booking.get("phone", "+919999999999") 
    await notification_service.send_sms(user_phone, f"Your booking has been cancelled. Reason: {body.reason}")
    
    await audit_service.write_log("booking.cancelled", booking_id=str(booking_id), admin_id=str(current_user.id))
    return {"message": "Booking cancelled"}
