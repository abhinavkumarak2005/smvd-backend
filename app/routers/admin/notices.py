from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.models.schemas.notice import NoticeCreateRequest, NoticeUpdateRequest, NoticeResponse
from app.services import notice_service
from app.repositories import notice_repo

router = APIRouter(tags=["Admin - Notices"])

@router.get("/admin/notices", response_model=list[NoticeResponse])
async def list_notices(
    status: str | None = Query(None, description="Filter by status: active, draft, scheduled, expired"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """List all notices with optional status filter and pagination."""
    return await notice_repo.get_all_notices(conn, status, page, limit)


@router.get("/admin/notices/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get full details of a specific notice."""
    notice = await notice_repo.get_notice(conn, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice


@router.post("/admin/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(
    body: NoticeCreateRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Create a new notice."""
    return await notice_service.create_notice(conn, UUID(current_user.id), body)


@router.put("/admin/notices/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: UUID,
    body: NoticeUpdateRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Update an existing notice."""
    notice = await notice_service.update_notice(conn, UUID(current_user.id), notice_id, body)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice


@router.patch("/admin/notices/{notice_id}/activate")
async def activate_notice(
    notice_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Activate a notice, making it visible to the public immediately."""
    notice = await notice_repo.get_notice(conn, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
        
    await notice_service.activate_now(conn, UUID(current_user.id), notice_id)
    return {"message": "Notice activated"}


@router.patch("/admin/notices/{notice_id}/deactivate")
async def deactivate_notice(
    notice_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Deactivate a notice, hiding it from the public immediately."""
    notice = await notice_repo.get_notice(conn, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
        
    await notice_service.deactivate_now(conn, UUID(current_user.id), notice_id)
    return {"message": "Notice deactivated"}


@router.delete("/admin/notices/{notice_id}", status_code=204)
async def delete_notice(
    notice_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Soft delete a notice (sets status to expired)."""
    notice = await notice_repo.get_notice(conn, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
        
    await notice_service.delete_notice(conn, UUID(current_user.id), notice_id)
