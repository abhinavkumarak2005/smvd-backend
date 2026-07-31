from fastapi import APIRouter, Depends
import asyncpg

from app.database import get_db
from app.models.schemas.notice import NoticeResponse
from app.services import notice_service

router = APIRouter(tags=["Notices (Public)"])

@router.get("/notices", response_model=list[NoticeResponse])
async def list_active_notices(conn: asyncpg.Connection = Depends(get_db)):
    """List all active, unexpired notices. No auth required."""
    return await notice_service.get_public_notices(conn)
