import re
from datetime import date
from uuid import UUID
import asyncpg
from fastapi import HTTPException

from app.models.schemas.certificate import CertificatePreferenceRequest
from app.repositories import certificate_repo, e_undiyal_repo
from app.services import notification_service, receipt_service, audit_service

_PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")

async def trigger_80g_workflow(conn: asyncpg.Connection, transaction_id: UUID) -> None:
    txn = await e_undiyal_repo.get_transaction(conn, transaction_id)
    if not txn or not txn["donor_phone"]:
        return
    
    await notification_service.send_sms(
        txn["donor_phone"],
        f"Thank you for your donation of ₹{txn['amount_paise'] // 100}. "
        "Your donation qualifies for 80G tax exemption. You will be contacted for certificate delivery."
    )
    if txn["donor_email"]:
        await notification_service.send_email(
            txn["donor_email"],
            subject="Donation Received - 80G Eligible"
        )


async def process_delivery_preference(conn: asyncpg.Connection, transaction_id: UUID, request: CertificatePreferenceRequest) -> None:
    txn = await e_undiyal_repo.get_transaction(conn, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn["certificate_status"] != "pending_details":
        raise HTTPException(status_code=409, detail="Preference already submitted or certificate in progress")
    
    phone = txn["donor_phone"]
    email = txn["donor_email"]

    pref_data = {
        "donor_location_type": request.donor_location_type,
        "delivery_mode": request.delivery_mode,
        "donor_address": request.donor_address.model_dump() if request.donor_address else None
    }

    if request.donor_location_type == "local":
        pref_data["delivery_mode"] = "in_person"
        await certificate_repo.update_delivery_preference(conn, transaction_id, pref_data)
        await notification_service.send_sms(
            phone,
            "Your 80G certificate will be ready for collection at the temple office. "
            "Please bring your original payment receipt and a valid photo ID. "
            "Office hours: 9:00 AM – 5:00 PM, Monday to Saturday."
        )
        if email:
            await notification_service.send_email(email, subject="80G Certificate - Local Collection")
            
    elif request.donor_location_type == "domestic":
        if not request.donor_address:
            raise HTTPException(status_code=422, detail="Address is required for domestic courier")
        if not request.donor_address.pan_number or not _PAN_REGEX.match(request.donor_address.pan_number):
            raise HTTPException(status_code=422, detail="Valid PAN is required for domestic tax certificate")
        if not request.donor_address.pincode.isdigit() or len(request.donor_address.pincode) != 6:
            raise HTTPException(status_code=422, detail="Pincode must be 6 digits")

        pref_data["delivery_mode"] = "courier"
        await certificate_repo.update_delivery_preference(conn, transaction_id, pref_data)
        await notification_service.send_sms(
            phone,
            "Your 80G certificate will be dispatched to your address via courier "
            "within 7–10 working days. You will receive a tracking number once dispatched."
        )
        
    elif request.donor_location_type == "international":
        if not request.donor_address:
            raise HTTPException(status_code=422, detail="Address is required for international courier")

        pref_data["delivery_mode"] = "courier"
        await certificate_repo.update_delivery_preference(conn, transaction_id, pref_data)
        await notification_service.send_sms(
            phone,
            "Your 80G certificate will be dispatched via international courier. "
            "Delivery typically takes 10–21 working days depending on your country. "
            "A tracking number will be shared via email once dispatched."
        )


async def issue_certificate(conn: asyncpg.Connection, transaction_id: UUID, cert_data: dict, admin_id: UUID) -> None:
    txn = await e_undiyal_repo.get_transaction(conn, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Generate certificate number
    current_year = date.today().year
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM e_undiyal_transactions WHERE certificate_status IN ('ready', 'dispatched', 'delivered') AND EXTRACT(YEAR FROM created_at) = $1",
        current_year
    )
    cert_number = f"SMV-80G-{current_year}-{count + 1:04d}"

    signed_url = await receipt_service.generate_certificate_pdf(transaction_id, cert_data)
    
    await certificate_repo.issue_certificate(conn, transaction_id, cert_number, signed_url, admin_id)

    phone = txn["donor_phone"]
    email = txn["donor_email"]
    
    await notification_service.send_sms(
        phone,
        f"Your 80G certificate (No: {cert_number}) is ready. Download: {signed_url}"
    )
    if email:
        await notification_service.send_email(email, certificate_url=signed_url)

    await audit_service.write_log("certificate.issued", transaction_id=str(transaction_id), admin_id=str(admin_id))
