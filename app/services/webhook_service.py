import hmac
import hashlib
import secrets
import logging
from uuid import UUID
import asyncpg
from fastapi import HTTPException

from app.config import get_settings
from app.repositories import slot_inventory_repo, booking_repo
from app.services import payment_service, audit_service, notification_service, receipt_service

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_signature(raw_body: bytes, signature: str) -> bool:
    if not signature:
        return False
        
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret or secret == "YOUR_VALUE_HERE":
        # Accept anything if secret is not configured correctly in dev
        logger.warning("RAZORPAY_WEBHOOK_SECRET is not configured properly, accepting signature blindly in DEV.")
        return True
        
    expected_mac = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    
    if not secrets.compare_digest(expected_mac, signature):
        logger.critical("Webhook signature mismatch! Expected: %s, Got: %s", expected_mac, signature)
        return False
        
    return True


async def process_payment_captured(conn: asyncpg.Connection, event_data: dict) -> None:
    gateway_order_id = event_data.get("order_id")
    gateway_payment_id = event_data.get("id")
    amount_paise = event_data.get("amount")
    
    if not gateway_order_id:
        logger.error("No order_id in webhook payload")
        return

    async with conn.transaction():
        payment = await conn.fetchrow(
            "SELECT * FROM payments WHERE gateway_order_id = $1 FOR UPDATE", 
            gateway_order_id
        )
        if not payment:
            logger.error("Payment record not found for order_id: %s", gateway_order_id)
            return
            
        if payment["status"] == "success":
            logger.info("Duplicate webhook for order_id %s, skipping.", gateway_order_id)
            return
            
        booking = await conn.fetchrow(
            "SELECT * FROM bookings WHERE id = $1 FOR UPDATE",
            payment["booking_id"]
        )
        if not booking:
            logger.error("Booking not found for payment: %s", payment["id"])
            return
            
        if booking["status"] != "pending_payment":
            logger.warning("Booking %s is not in pending_payment state (status: %s).", booking["id"], booking["status"])
            return
            
        if payment["amount_paise"] != amount_paise:
            logger.error("Amount mismatch for order_id %s: expected %s, got %s", gateway_order_id, payment["amount_paise"], amount_paise)
            return
            
        slot = await conn.fetchrow(
            "SELECT * FROM slot_inventory WHERE id = $1 FOR UPDATE",
            booking["slot_id"]
        )
        if not slot:
            logger.error("Slot not found for booking: %s", booking["id"])
            return

        # Final capacity check (edge cases)
        total_booked = slot["confirmed_count"] + slot["pending_count"]
        if slot["total_capacity"] > 0 and total_booked > slot["total_capacity"]:
            # Slot got overbooked somehow (maybe due to concurrent webhook and manual admin block?)
            # Since user already paid, we must refund them.
            logger.warning("Slot over capacity during webhook for booking %s. Initiating refund.", booking["id"])
            await payment_service.initiate_refund(gateway_payment_id, amount_paise)
            await conn.execute("UPDATE bookings SET status = 'rejected' WHERE id = $1", booking["id"])
            await conn.execute("UPDATE payments SET status = 'refunded', gateway_payment_id = $2 WHERE id = $1", payment["id"], gateway_payment_id)
            return
            
        new_status = "pending_approval" if booking["requires_approval"] else "confirmed"
        
        await conn.execute(
            "UPDATE bookings SET status = $1, updated_at = NOW() WHERE id = $2",
            new_status, booking["id"]
        )
        
        # We assume pending_count is already incremented when booking was created in Day 3.
        # Now we move pending -> confirmed
        await slot_inventory_repo.confirm_slot(conn, booking["slot_id"])
        
        await conn.execute(
            "UPDATE payments SET status = 'success', gateway_payment_id = $1, paid_at = NOW(), updated_at = NOW() WHERE id = $2",
            gateway_payment_id, payment["id"]
        )
        
        if new_status == "confirmed":
            await audit_service.write_log("payment.success", booking_id=booking["id"])
            await notification_service.send_sms(str(booking["user_id"]), f"Payment successful for booking {booking['id']}")
            await receipt_service.generate_receipt_pdf(booking["id"])


async def process_payment_failed(conn: asyncpg.Connection, event_data: dict) -> None:
    gateway_order_id = event_data.get("order_id")
    if not gateway_order_id:
        return
        
    async with conn.transaction():
        payment = await conn.fetchrow("SELECT * FROM payments WHERE gateway_order_id = $1", gateway_order_id)
        if not payment:
            return
            
        await conn.execute("UPDATE payments SET status = 'failed', updated_at = NOW() WHERE id = $1", payment["id"])
        
        booking = await conn.fetchrow("SELECT * FROM bookings WHERE id = $1 FOR UPDATE", payment["booking_id"])
        if not booking:
            return
            
        await conn.execute("SELECT * FROM slot_inventory WHERE id = $1 FOR UPDATE", booking["slot_id"])
        await slot_inventory_repo.decrement_pending(conn, booking["slot_id"])
        
        await conn.execute("UPDATE bookings SET status = 'payment_failed', updated_at = NOW() WHERE id = $1", booking["id"])
