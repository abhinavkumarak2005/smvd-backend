from uuid import UUID
import asyncpg

from app.repositories import e_undiyal_repo, payment_repo
from app.services import payment_service
from app.config import get_settings
from app.models.schemas.e_undiyal import DonationInitiateRequest, DonationInitiateResponse

settings = get_settings()

_MIN_AMOUNT = 10_000  # ₹100 minimum in paise


async def initiate_donation(
    conn: asyncpg.Connection,
    request: DonationInitiateRequest,
    user_id: str | None,
) -> DonationInitiateResponse:
    if request.amount_paise < _MIN_AMOUNT:
        from fastapi import HTTPException
        raise HTTPException(422, f"Minimum donation is ₹100 ({_MIN_AMOUNT} paise)")

    # 1. Create e_undiyal transaction record
    transaction = await e_undiyal_repo.create_transaction(conn, {
        "user_id": user_id,
        "donor_name": request.donor_name,
        "donor_phone": request.donor_phone,
        "donor_email": request.donor_email,
        "amount_paise": request.amount_paise,
        "donation_category": request.donation_category,
    })

    transaction_id = transaction["id"]
    reference = transaction["transaction_reference"]

    # 2. Create Razorpay order (or dev stub)
    order = await payment_service.create_order(
        amount_paise=request.amount_paise,
        receipt=reference,
    )

    # 3. Record the payment row (booking_id = None → this is E-Undiyal)
    await payment_repo.create_payment_record(
        conn=conn,
        gateway_order_id=order["id"],
        amount_paise=request.amount_paise,
        booking_id=None,
        e_undiyal_id=transaction_id,
    )

    return DonationInitiateResponse(
        transaction_id=str(transaction_id),
        transaction_reference=reference,
        gateway_order_id=order["id"],
        amount_paise=request.amount_paise,
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
    )


async def complete_donation(
    conn: asyncpg.Connection,
    transaction_id: UUID,
    gateway_payment_id: str,
) -> None:
    """Called by webhook when payment.captured for E-Undiyal. Day 6 webhook wires this up."""
    await e_undiyal_repo.update_status(conn, transaction_id, "success")
    await payment_repo.update_payment_status(
        conn=conn,
        gateway_order_id=gateway_payment_id,  # note: webhook has both IDs
        status="success",
        gateway_payment_id=gateway_payment_id,
    )
    # 80G workflow triggered from webhook_service (Day 6)
    # notification_service called from webhook_service as BackgroundTask (Day 6)
