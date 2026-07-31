from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def generate_certificate_pdf(transaction_id: UUID, cert_data: dict) -> str:
    """Stub for PDF generation and upload, returning a fake signed URL."""
    logger.info("PDF STUB: Generate 80G for txn=%s", transaction_id)
    return f"https://supabase.co/storage/v1/object/public/donation-receipts/SMV-80G-{transaction_id}.pdf"

async def generate_receipt_pdf(booking_id: UUID) -> str:
    """Stub for generating a booking receipt PDF."""
    logger.info("PDF STUB: Generate Receipt for booking=%s", booking_id)
    return f"https://supabase.co/storage/v1/object/public/receipts/REC-{booking_id}.pdf"
