import logging
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_DEV_MODE = (
    not settings.RAZORPAY_KEY_ID
    or settings.RAZORPAY_KEY_ID == "YOUR_VALUE_HERE"
)

async def create_order(amount_paise: int, receipt: str) -> dict:
    """
    Create a Razorpay order.
    In development (no real keys), returns a stub order so the flow can be tested end-to-end.
    """
    if _DEV_MODE:
        return {
            "id": f"order_DEV_{uuid4().hex[:14]}",
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
        }

    try:
        import razorpay  # noqa: PLC0415
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        return client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
        })
    except Exception as e:
        logger.error("Razorpay order creation failed: %s", e)
        raise HTTPException(status_code=503, detail="Payment service unavailable")

async def initiate_refund(payment_id: str, amount_paise: int) -> dict:
    if _DEV_MODE:
        logger.info("PAYMENT STUB: Initiating refund of %d paise for payment %s", amount_paise, payment_id)
        return {"id": f"refund_DEV_{uuid4().hex[:14]}"}
        
    try:
        import razorpay  # noqa: PLC0415
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        refund = client.payment.refund(payment_id, {"amount": amount_paise})
        logger.info("Initiated refund %s for payment %s", refund["id"], payment_id)
        return refund
    except Exception as e:
        logger.error("Razorpay refund failed: %s", e)
        # We don't raise 503 here because refund might happen in a background process or webhook handler.
        # Just return empty or raise a specific internal exception depending on requirements.
        raise Exception(f"Refund failed: {str(e)}")
