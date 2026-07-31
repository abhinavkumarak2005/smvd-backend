from uuid import UUID
from pydantic import BaseModel


class ServiceResponse(BaseModel):
    id: UUID
    name: str
    name_tamil: str | None
    category: str | None
    description: str | None
    description_tamil: str | None
    price_paise: int
    max_persons: int
    advance_booking_days: int
    session: str
    is_active: bool
    image_url: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class ServiceCreateRequest(BaseModel):
    name: str
    name_tamil: str | None = None
    category: str | None = None
    description: str | None = None
    description_tamil: str | None = None
    price_paise: int
    max_persons: int = 5
    advance_booking_days: int = 1
    session: str = "na"
    image_url: str | None = None
    sort_order: int = 0


class ServiceUpdateRequest(BaseModel):
    """All fields optional — only provided fields are updated."""
    name: str | None = None
    name_tamil: str | None = None
    category: str | None = None
    description: str | None = None
    description_tamil: str | None = None
    price_paise: int | None = None
    max_persons: int | None = None
    advance_booking_days: int | None = None
    session: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
