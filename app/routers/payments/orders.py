from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.models.schemas.payment import PaymentOrderResponse
from app.repositories import booking_repo, payment_repo
from app.services import payment_service
from app.config import get_settings

router = APIRouter(tags=["Payments"])
settings = get_settings()

class CreateOrderRequest(BaseModel):
    booking_id: UUID

@router.post("/payments/create-order", response_model=PaymentOrderResponse)
async def create_payment_order(
    request: CreateOrderRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("devotee")),
):
    """Create a Razorpay order for an existing booking."""
    booking = await booking_repo.get_booking(conn, request.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if str(booking["user_id"]) != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay for this booking")
        
    if booking["status"] != "pending_payment":
        raise HTTPException(status_code=409, detail=f"Booking cannot be paid for in status: {booking['status']}")

    # Check if a payment record already exists
    payment_record = await conn.fetchrow(
        "SELECT * FROM payments WHERE booking_id = $1 ORDER BY created_at DESC LIMIT 1",
        str(request.booking_id)
    )
    
    if payment_record and payment_record["status"] == "initiated":
        # Idempotent return of existing order
        return PaymentOrderResponse(
            gateway_order_id=payment_record["gateway_order_id"],
            amount_paise=payment_record["amount_paise"],
            currency=payment_record["currency"],
            razorpay_key_id=settings.RAZORPAY_KEY_ID if settings.RAZORPAY_KEY_ID != "YOUR_VALUE_HERE" else "DEV_MODE_KEY"
        )
        
    # If no valid pending order exists, create one
    order = await payment_service.create_order(booking["amount_paise"], str(request.booking_id)[:40])
    await payment_repo.create_payment_record(conn, request.booking_id, order["id"], booking["amount_paise"])
    
    return PaymentOrderResponse(
        gateway_order_id=order["id"],
        amount_paise=booking["amount_paise"],
        currency="INR",
        razorpay_key_id=settings.RAZORPAY_KEY_ID if settings.RAZORPAY_KEY_ID != "YOUR_VALUE_HERE" else "DEV_MODE_KEY"
    )
