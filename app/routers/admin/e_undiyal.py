from datetime import date
from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.repositories import e_undiyal_repo

router = APIRouter(tags=["Admin - E-Undiyal"])

@router.get("/admin/e-undiyal")
async def list_e_undiyal_transactions(
    status: str | None = Query(None),
    transaction_date: date | None = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """List all e-undiyal transactions with optional filters and pagination."""
    query = "SELECT * FROM e_undiyal_transactions WHERE 1=1"
    args = []
    
    if status:
        args.append(status)
        query += f" AND status = ${len(args)}"
        
    if transaction_date:
        args.append(transaction_date)
        query += f" AND DATE(created_at) = ${len(args)}"
        
    offset = (page - 1) * limit
    args.extend([limit, offset])
    query += f" ORDER BY created_at DESC LIMIT ${len(args) - 1} OFFSET ${len(args)}"
    
    rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]


@router.get("/admin/e-undiyal/{transaction_id}")
async def get_e_undiyal_transaction(
    transaction_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get full details of a specific e-undiyal transaction."""
    txn = await e_undiyal_repo.get_transaction(conn, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
