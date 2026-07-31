from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field


class PersonRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    star: str = Field(min_length=2, max_length=50)


class PersonResponse(BaseModel):
    id: UUID
    full_name: str
    star: str

    model_config = {"from_attributes": True}


class BookingCreateRequest(BaseModel):
    service_id: UUID
    booking_date: date
    session: Literal["morning", "evening", "na"] = "na"
    num_persons: int = Field(default=1, ge=1, le=5)
    persons: list[PersonRequest] = Field(min_length=1, max_length=5)


class BookingResponse(BaseModel):
    id: UUID
    booking_reference: str
    service_id: UUID
    service_name: str
    booking_date: date
    session: str
    num_persons: int
    amount_paise: int
    status: str
    requires_approval: bool
    special_note: str | None
    persons: list[PersonResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    bookings: list[BookingResponse]
    total: int
    page: int
    limit: int
