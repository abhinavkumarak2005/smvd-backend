import re
from typing import Literal
from pydantic import BaseModel, EmailStr, field_validator

_E164 = re.compile(r"^\+[1-9]\d{1,14}$")


class DonationInitiateRequest(BaseModel):
    donor_name: str
    donor_phone: str
    donor_email: EmailStr | None = None
    amount_paise: int  # minimum 10000 (₹100) — validated in service layer
    donation_category: str | None = None

    @field_validator("donor_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _E164.match(v):
            raise ValueError("Phone must be E.164 format e.g. +919876543210")
        return v


class DonationInitiateResponse(BaseModel):
    transaction_id: str
    transaction_reference: str
    gateway_order_id: str
    amount_paise: int
    razorpay_key_id: str
    message_80g: str = "This donation qualifies for 80G tax exemption"
