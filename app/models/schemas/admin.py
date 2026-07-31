from uuid import UUID
from typing import Literal
from pydantic import BaseModel
from app.models.schemas.service import ServiceCreateRequest, ServiceUpdateRequest


class AdminServiceCreateRequest(ServiceCreateRequest):
    """Admin creates a service — same as public create, can set is_active."""
    is_active: bool = True


class AdminServiceUpdateRequest(ServiceUpdateRequest):
    """Admin updates a service — all fields optional."""
    pass


class AdminServiceToggleRequest(BaseModel):
    is_active: bool


class CalendarDateCreateRequest(BaseModel):
    date: str           # YYYY-MM-DD
    status: str         # open | blocked | partial
    notes: str | None = None
    notes_tamil: str | None = None
    allowed_service_ids: list[UUID] = []


class CalendarDateResponse(BaseModel):
    id: UUID
    date: str
    status: str
    notes: str | None
    notes_tamil: str | None
    allowed_service_ids: list

    model_config = {"from_attributes": True}


class UserAdminResponse(BaseModel):
    id: UUID
    phone: str | None
    email: str | None
    full_name: str | None
    role: str
    is_active: bool
    created_at: str
    booking_count: int = 0
    donation_total: int = 0

    model_config = {"from_attributes": True}


class UserRoleUpdateRequest(BaseModel):
    role: Literal["devotee", "staff", "admin", "super_admin"]
