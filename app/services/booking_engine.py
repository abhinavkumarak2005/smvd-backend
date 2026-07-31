import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4
import asyncpg
from fastapi import HTTPException
from pydantic import BaseModel

from app.models.schemas.booking import BookingCreateRequest
from app.repositories import booking_repo, slot_inventory_repo, service_repo, payment_repo
from app.services import calendar_service, conflict_checker, payment_service

logger = logging.getLogger(__name__)


class BookingResult(BaseModel):
    booking_id: UUID
    reference_number: str
    gateway_order_id: str
    amount_paise: int
    requires_approval: bool
    notice: str | None = None


def generate_reference() -> str:
    return f"SMV-{uuid4().hex[:8].upper()}"


async def create_booking(conn: asyncpg.Connection, user_id: UUID, request: BookingCreateRequest) -> BookingResult:
    # STEP 2: Calendar Check
    date_status = await calendar_service.check_date(conn, request.booking_date, request.service_id)
    if date_status.status == "blocked":
        raise HTTPException(status_code=409, detail=f"DATE_BLOCKED: {date_status.notes or 'Date is blocked'}")

    # STEP 3: Service Check & Advance Booking validation
    repo = service_repo.ServiceRepo(conn)
    service = await repo.get_service(request.service_id)
    if not service or not service["is_active"]:
        raise HTTPException(status_code=404, detail="Service not found or inactive")
        
    today = datetime.now(timezone.utc).date()
    if request.booking_date < today:
        raise HTTPException(status_code=422, detail="Cannot book in the past")

    min_date = today + timedelta(days=service["advance_booking_days"])
    if request.booking_date < min_date:
        raise HTTPException(status_code=422, detail=f"ADVANCE_DAYS: Must book at least {service['advance_booking_days']} days in advance")

    # STEP 4: Conflict rules check
    conflict_res = await conflict_checker.check_conflicts(conn, request.service_id, request.booking_date, request.session)
    if conflict_res.blocked:
        raise HTTPException(status_code=409, detail=f"CONFLICT_RULE: {conflict_res.message}")

    # Start transaction explicitly
    async with conn.transaction():
        # STEP 5: Slot Inventory Management
        slot = await slot_inventory_repo.get_or_create_slot(
            conn, request.service_id, request.booking_date, request.session, service["default_capacity"]
        )
        
        slot_for_update = await slot_inventory_repo.get_slot_for_update(
            conn, request.service_id, request.booking_date, request.session
        )
        if not slot_for_update:
            raise HTTPException(status_code=500, detail="Failed to acquire slot lock")
            
        if slot_for_update["is_blocked"]:
            raise HTTPException(status_code=409, detail=f"SLOT_BLOCKED: {slot_for_update['block_reason']}")
            
        # Capacity check
        total_booked = slot_for_update["confirmed_count"] + slot_for_update["pending_count"]
        # Treat total_capacity = 0 as unlimited for now, though usually it means blocked.
        if slot_for_update["total_capacity"] > 0 and total_booked >= slot_for_update["total_capacity"]:
            raise HTTPException(status_code=409, detail="SLOT_FULL: This slot is fully booked")
            
        await slot_inventory_repo.increment_pending(conn, slot_for_update["id"])

        # STEP 6: Duplicate Check
        is_duplicate = await booking_repo.check_duplicate(
            conn, user_id, request.service_id, request.booking_date, request.session
        )
        if is_duplicate:
            raise HTTPException(status_code=409, detail="DUPLICATE_BOOKING: You already have a booking for this service on this date/session")

        # STEP 7: Special Rules
        if "Moolavar Abishegam" in service["name"]:
            if len(request.persons) > 3:
                raise HTTPException(status_code=422, detail="Moolavar Abishegam allows maximum 3 persons per family")
        if "Annadhanam" in service["name"]:
            if request.num_persons != 1:
                raise HTTPException(status_code=422, detail="Annadhanam bookings require exactly 1 primary person")

        # STEP 8: Create Booking
        initial_status = "pending_approval" if conflict_res.requires_approval else "pending_payment"
        reference_number = generate_reference()
        
        booking_data = {
            "user_id": str(user_id),
            "service_id": str(request.service_id),
            "booking_date": request.booking_date,
            "session": request.session,
            "slot_id": str(slot_for_update["id"]),
            "status": initial_status,
            "reference_number": reference_number,
            "notes": conflict_res.notice,
            "amount_paise": service["price_paise"],
            "requires_approval": conflict_res.requires_approval
        }
        
        booking = await booking_repo.create_booking(conn, booking_data)
        
        # Insert persons
        persons_data = [p.model_dump() for p in request.persons]
        await booking_repo.insert_persons(conn, booking["id"], persons_data)

        # STEP 9: Payment Gateway Order
        try:
            order = await payment_service.create_order(service["price_paise"], str(booking["id"])[:40])
            await payment_repo.create_payment_record(conn, booking["id"], order["id"], service["price_paise"])
        except Exception as e:
            logger.error("Payment Gateway Error: %s", e)
            raise HTTPException(status_code=503, detail="Payment service unavailable")

        # STEP 10: Transaction commits implicitly here when block exits

    return BookingResult(
        booking_id=booking["id"],
        reference_number=reference_number,
        gateway_order_id=order["id"],
        amount_paise=service["price_paise"],
        requires_approval=conflict_res.requires_approval,
        notice=conflict_res.notice
    )
