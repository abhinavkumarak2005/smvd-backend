from pydantic import BaseModel

class PaymentOrderResponse(BaseModel):
    gateway_order_id: str
    amount_paise: int
    currency: str
    razorpay_key_id: str | None = None

class PaymentStatusResponse(BaseModel):
    status: str
    gateway_payment_id: str | None = None
    paid_at: str | None = None
