from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.models.schemas.admin import UserAdminResponse, UserRoleUpdateRequest
from app.repositories import user_repo, e_undiyal_repo

router = APIRouter(tags=["Admin - Users"])


@router.get("/admin/users", response_model=list[UserAdminResponse])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """List all users with optional role filter and pagination."""
    users = await user_repo.get_all_users(conn, page, limit, role)
    for user in users:
        summary = await user_repo.get_user_booking_summary(conn, user["id"])
        donation_summary = await user_repo.get_user_donation_summary(conn, user["id"])
        user["booking_count"] = summary["booking_count"]
        user["donation_total"] = donation_summary["donation_total"]
        user["created_at"] = str(user["created_at"])
    return users


@router.get("/admin/users/search", response_model=list[UserAdminResponse])
async def search_users(
    q: str = Query(..., min_length=3),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Search users by phone, email, or full name."""
    users = await user_repo.search_users(conn, q)
    for user in users:
        summary = await user_repo.get_user_booking_summary(conn, user["id"])
        donation_summary = await user_repo.get_user_donation_summary(conn, user["id"])
        user["booking_count"] = summary["booking_count"]
        user["donation_total"] = donation_summary["donation_total"]
        user["created_at"] = str(user["created_at"])
    return users


@router.get("/admin/users/{user_id}", response_model=UserAdminResponse)
async def get_user_detail(
    user_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get full details of a specific user."""
    user = await user_repo.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    summary = await user_repo.get_user_booking_summary(conn, user["id"])
    donation_summary = await user_repo.get_user_donation_summary(conn, user["id"])
    user["booking_count"] = summary["booking_count"]
    user["donation_total"] = donation_summary["donation_total"]
    user["created_at"] = str(user["created_at"])
    return user


@router.get("/admin/users/{user_id}/donations")
async def get_user_donations(
    user_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """List all e-undiyal donations by a user."""
    user = await user_repo.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await e_undiyal_repo.get_user_transactions(conn, str(user_id))


@router.get("/admin/users/{user_id}/bookings")
async def get_user_bookings(
    user_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """List all bookings by a user. (Stub until Day 7)"""
    return {"message": "Stub: Bookings for user"}


@router.patch("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    body: UserRoleUpdateRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("super_admin")),
):
    """Update a user's role. Requires super_admin."""
    user = await user_repo.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await user_repo.update_user_role(conn, user_id, body.role)
    from app.services import audit_service
    await audit_service.write_log("user.role_updated", user_id=str(user_id), new_role=body.role, admin_id=str(current_user.id))
    return {"message": f"User role updated to {body.role}"}


@router.patch("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Deactivate a user's account."""
    user = await user_repo.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await user_repo.deactivate_user(conn, user_id)
    from app.services import audit_service
    await audit_service.write_log("user.deactivated", user_id=str(user_id), admin_id=str(current_user.id))
    return {"message": "User deactivated"}
