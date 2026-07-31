from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class NoticeCreateRequest(BaseModel):
    title: str
    title_tamil: str | None = None
    body: str
    body_tamil: str | None = None
    category: str | None = None
    priority: int = 0
    status: str = "draft"  # active, draft, scheduled
    published_at: datetime | None = None
    expires_at: datetime | None = None


class NoticeUpdateRequest(BaseModel):
    title: str | None = None
    title_tamil: str | None = None
    body: str | None = None
    body_tamil: str | None = None
    category: str | None = None
    priority: int | None = None
    status: str | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None


class NoticeResponse(BaseModel):
    id: UUID
    title: str
    title_tamil: str | None
    body: str
    body_tamil: str | None
    category: str | None
    status: str
    priority: int
    published_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
