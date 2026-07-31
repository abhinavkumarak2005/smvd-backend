import logging
from fastapi import APIRouter, Request, HTTPException, Depends
import asyncpg

from app.database import get_db
from app.services import webhook_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Payments - Webhook"])

@router.post("/payments/webhook")
async def razorpay_webhook(
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    """Handle incoming webhooks from Razorpay."""
    raw_body = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    
    if not webhook_service.verify_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    event_type = payload.get("event")
    payload_entity = payload.get("payload", {})
    
    if event_type == "payment.captured":
        payment_entity = payload_entity.get("payment", {}).get("entity", {})
        await webhook_service.process_payment_captured(conn, payment_entity)
        
    elif event_type == "payment.failed":
        payment_entity = payload_entity.get("payment", {}).get("entity", {})
        await webhook_service.process_payment_failed(conn, payment_entity)
        
    else:
        logger.info("Ignored webhook event: %s", event_type)
        
    return {"status": "ok"}
