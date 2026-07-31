from uuid import UUID
import asyncpg


async def update_delivery_preference(conn: asyncpg.Connection, transaction_id: UUID, preference_data: dict) -> None:
    import json
    address = preference_data.get("donor_address")
    address_json = json.dumps(address) if address else None

    await conn.execute(
        """
        UPDATE e_undiyal_transactions SET
            delivery_mode = $1,
            donor_location_type = $2,
            donor_address = $3,
            certificate_status = 'processing',
            details_submitted_at = NOW(),
            updated_at = NOW()
        WHERE id = $4
        """,
        preference_data.get("delivery_mode"),
        preference_data.get("donor_location_type"),
        address_json,
        str(transaction_id),
    )


async def issue_certificate(conn: asyncpg.Connection, transaction_id: UUID, cert_number: str, cert_url: str, admin_id: UUID) -> None:
    await conn.execute(
        """
        UPDATE e_undiyal_transactions SET
            certificate_number = $1,
            certificate_url = $2,
            certificate_status = 'ready',
            certificate_issued_by = $3,
            certificate_issued_at = NOW(),
            updated_at = NOW()
        WHERE id = $4
        """,
        cert_number,
        cert_url,
        str(admin_id),
        str(transaction_id),
    )


async def mark_dispatched(conn: asyncpg.Connection, transaction_id: UUID, courier_partner: str, tracking_id: str) -> None:
    await conn.execute(
        """
        UPDATE e_undiyal_transactions SET
            courier_partner = $1,
            courier_tracking_id = $2,
            certificate_status = 'dispatched',
            dispatched_at = NOW(),
            updated_at = NOW()
        WHERE id = $3
        """,
        courier_partner,
        tracking_id,
        str(transaction_id),
    )


async def mark_delivered(conn: asyncpg.Connection, transaction_id: UUID) -> None:
    await conn.execute(
        """
        UPDATE e_undiyal_transactions SET
            certificate_status = 'delivered',
            updated_at = NOW()
        WHERE id = $1
        """,
        str(transaction_id),
    )


async def get_certificate_status(conn: asyncpg.Connection, transaction_id: UUID) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT certificate_status, delivery_mode, courier_tracking_id, certificate_url, user_id
        FROM e_undiyal_transactions
        WHERE id = $1
        """,
        str(transaction_id),
    )
    return dict(row) if row else None


async def get_pending_certificates(conn: asyncpg.Connection, status: str, page: int = 1, limit: int = 20) -> list[dict]:
    offset = (page - 1) * limit
    rows = await conn.fetch(
        "SELECT * FROM e_undiyal_transactions WHERE certificate_status = $1 ORDER BY created_at ASC LIMIT $2 OFFSET $3",
        status, limit, offset
    )
    return [dict(r) for r in rows]
