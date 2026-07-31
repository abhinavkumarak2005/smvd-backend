from datetime import date
from uuid import UUID
from pydantic import BaseModel
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.repositories import slot_inventory_repo
from app.services import audit_service

router = APIRouter(tags=["Admin - Inventory"])

class BlockSlotRequest(BaseModel):
    reason: str

class UpdateCapacityRequest(BaseModel):
    total_capacity: int

@router.get("/admin/inventory")
async def get_inventory(
    service_id: UUID,
    start_date: date,
    end_date: date,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """View slot inventory across a date range."""
    return await slot_inventory_repo.get_inventory(conn, service_id, start_date, end_date)

@router.patch("/admin/inventory/{slot_id}/block")
async def block_slot(
    slot_id: UUID,
    body: BlockSlotRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Block a specific slot from further bookings."""
    await slot_inventory_repo.block_slot(conn, slot_id, body.reason)
    await audit_service.write_log("slot.blocked", slot_id=str(slot_id), reason=body.reason, admin_id=str(current_user.id))
    return {"message": "Slot blocked"}

@router.patch("/admin/inventory/{slot_id}/capacity")
async def update_capacity(
    slot_id: UUID,
    body: UpdateCapacityRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("super_admin")),
):
    """Update total capacity for a specific slot. Requires super_admin."""
    await slot_inventory_repo.update_capacity(conn, slot_id, body.total_capacity)
    await audit_service.write_log("slot.capacity_updated", slot_id=str(slot_id), total_capacity=body.total_capacity, admin_id=str(current_user.id))
    return {"message": "Slot capacity updated"}
