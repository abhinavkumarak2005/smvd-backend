from uuid import UUID
from datetime import datetime, timezone
import asyncpg
import logging

from app.repositories import notice_repo
from app.services import audit_service
from app.models.schemas.notice import NoticeCreateRequest, NoticeUpdateRequest

logger = logging.getLogger(__name__)


async def get_public_notices(conn: asyncpg.Connection) -> list[dict]:
    return await notice_repo.get_active_notices(conn)


async def create_notice(conn: asyncpg.Connection, admin_id: UUID, request: NoticeCreateRequest) -> dict:
    data = request.model_dump()
    
    # Auto-activate if scheduled for the past
    if data["status"] == "scheduled" and data["published_at"] and data["published_at"] <= datetime.now(timezone.utc):
        data["status"] = "active"

    notice = await notice_repo.create_notice(conn, data)
    await audit_service.write_log("notice.created", notice_id=str(notice["id"]), admin_id=str(admin_id))
    return notice


async def update_notice(conn: asyncpg.Connection, admin_id: UUID, notice_id: UUID, request: NoticeUpdateRequest) -> dict | None:
    data = request.model_dump()
    notice = await notice_repo.update_notice(conn, notice_id, data)
    if notice:
        await audit_service.write_log("notice.updated", notice_id=str(notice_id), admin_id=str(admin_id))
    return notice


async def activate_now(conn: asyncpg.Connection, admin_id: UUID, notice_id: UUID) -> None:
    await notice_repo.activate_notice(conn, notice_id)
    await audit_service.write_log("notice.activated", notice_id=str(notice_id), admin_id=str(admin_id))


async def deactivate_now(conn: asyncpg.Connection, admin_id: UUID, notice_id: UUID) -> None:
    await notice_repo.deactivate_notice(conn, notice_id)
    await audit_service.write_log("notice.deactivated", notice_id=str(notice_id), admin_id=str(admin_id))


async def delete_notice(conn: asyncpg.Connection, admin_id: UUID, notice_id: UUID) -> None:
    await notice_repo.delete_notice(conn, notice_id)
    await audit_service.write_log("notice.deleted", notice_id=str(notice_id), admin_id=str(admin_id))


async def run_scheduler() -> None:
    """Called by APScheduler every 5 minutes."""
    from app.database import _pool
    
    if _pool is None:
        logger.error("Database pool not initialized for scheduler")
        return
        
    try:
        async with _pool.acquire() as conn:
            n_activated = await notice_repo.activate_scheduled(conn)
            n_expired = await notice_repo.expire_old(conn)
            logger.info("Notices: activated=%d, expired=%d", n_activated, n_expired)
    except Exception as e:
        logger.error("Error in notice scheduler: %s", e)
