from uuid import UUID
from pydantic import BaseModel
import asyncpg
from fastapi import APIRouter, Depends, Query, HTTPException

from app.database import get_db
from app.dependencies.auth import CurrentUser, require_role
from app.services import certificate_service, notification_service, audit_service
from app.repositories import certificate_repo, e_undiyal_repo

router = APIRouter(tags=["Admin - Certificates"])


class CertificateIssueRequest(BaseModel):
    certificate_data: dict = {}


class CertificateDispatchRequest(BaseModel):
    courier_partner: str
    courier_tracking_id: str


@router.get("/admin/certificates")
async def list_pending_certificates(
    status: str = Query("processing"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Get certificates by status (e.g. processing, ready, dispatched, delivered) with pagination."""
    return await certificate_repo.get_pending_certificates(conn, status, page, limit)


@router.post("/admin/certificates/{transaction_id}/issue")
async def issue_certificate(
    transaction_id: UUID,
    body: CertificateIssueRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Issue a PDF certificate."""
    await certificate_service.issue_certificate(conn, transaction_id, body.certificate_data, UUID(current_user.id))
    return {"message": "Certificate issued"}


@router.post("/admin/certificates/{transaction_id}/dispatch")
async def dispatch_certificate(
    transaction_id: UUID,
    body: CertificateDispatchRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Mark a certificate as dispatched via courier."""
    txn = await e_undiyal_repo.get_transaction(conn, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    await certificate_repo.mark_dispatched(conn, transaction_id, body.courier_partner, body.courier_tracking_id)
    
    if txn["donor_phone"]:
        await notification_service.send_sms(
            txn["donor_phone"],
            f"Your 80G certificate has been dispatched via {body.courier_partner}. Tracking ID: {body.courier_tracking_id}"
        )
    
    await audit_service.write_log("certificate.dispatched", transaction_id=str(transaction_id), admin_id=str(current_user.id))
    return {"message": "Certificate dispatched"}


@router.post("/admin/certificates/{transaction_id}/collected")
async def collect_certificate(
    transaction_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """Mark a certificate as collected in person."""
    txn = await e_undiyal_repo.get_transaction(conn, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    await certificate_repo.mark_delivered(conn, transaction_id)
    await audit_service.write_log("certificate.collected", transaction_id=str(transaction_id), admin_id=str(current_user.id))
    return {"message": "Certificate collected in person"}
