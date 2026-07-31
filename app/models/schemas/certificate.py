from typing import Literal
from pydantic import BaseModel


class DonorAddress(BaseModel):
    full_name: str
    door_no: str
    street: str
    city: str
    state: str
    pincode: str
    country: str
    phone: str
    pan_number: str | None = None


class CertificatePreferenceRequest(BaseModel):
    delivery_mode: Literal["in_person", "courier"]
    donor_location_type: Literal["local", "domestic", "international"]
    donor_address: DonorAddress | None = None  # required if delivery_mode == 'courier'


class CertificateStatusResponse(BaseModel):
    transaction_id: str
    certificate_status: str
    certificate_number: str | None
    certificate_url: str | None
    courier_tracking_id: str | None
    courier_partner: str | None
    dispatched_at: str | None
