from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.dependencies.auth import CurrentUser, get_optional_user, require_role
from app.models.schemas.e_undiyal import DonationInitiateRequest, DonationInitiateResponse
from app.repositories import e_undiyal_repo
from app.services import e_undiyal_service

router = APIRouter(tags=["E-Undiyal"])


@router.post("/e-undiyal/initiate", response_model=DonationInitiateResponse, status_code=201)
async def initiate_donation(
    body: DonationInitiateRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    """
    Initiate a donation. Auth is optional — logged-in users are linked, guests donate anonymously.
    Returns a Razorpay order ID to complete payment on the frontend.
    """
    user_id = current_user.id if current_user else None
    return await e_undiyal_service.initiate_donation(conn, body, user_id)


@router.get("/e-undiyal/{transaction_id}")
async def get_donation(
    transaction_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("devotee")),
):
    """Get own donation transaction details + certificate status. Auth required."""
    txn = await e_undiyal_repo.get_transaction(conn, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn["user_id"] and str(txn["user_id"]) != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return txn


@router.get("/e-undiyal")
async def list_my_donations(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("devotee")),
):
    """List all donations made by the authenticated user."""
    return await e_undiyal_repo.get_user_transactions(conn, current_user.id)
