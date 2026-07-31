from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role, get_optional_user
from app.models.schemas.certificate import CertificatePreferenceRequest
from app.services import certificate_service
from app.repositories import certificate_repo

router = APIRouter(tags=["Certificates (E-Undiyal)"])

@router.post("/e-undiyal/{transaction_id}/certificate-preference")
async def submit_certificate_preference(
    transaction_id: UUID,
    body: CertificatePreferenceRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    """
    Submit preference for 80G certificate delivery.
    Auth is optional (allows guests using signed link or logged-in users).
    """
    await certificate_service.process_delivery_preference(conn, transaction_id, body)
    
    msg = "Preference submitted."
    if body.donor_location_type == "local":
        msg += " Your certificate will be ready for collection at the temple office."
    elif body.donor_location_type == "domestic":
        msg += " Your certificate will be dispatched via domestic courier."
    elif body.donor_location_type == "international":
        msg += " Your certificate will be dispatched via international courier."
        
    return {"message": msg}


@router.get("/e-undiyal/{transaction_id}/certificate-status")
async def get_certificate_status(
    transaction_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("devotee")),
):
    """Get the current status of the 80G certificate. Auth required."""
    status_data = await certificate_repo.get_certificate_status(conn, transaction_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    # Security: only admin or the donor can view
    if current_user.role == "devotee" and status_data["user_id"] and str(status_data["user_id"]) != current_user.id:
         raise HTTPException(status_code=403, detail="Access denied")

    # Remove user_id from response
    status_data.pop("user_id", None)
    return status_data
