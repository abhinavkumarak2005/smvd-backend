from datetime import date
from uuid import UUID
import asyncpg


def _generate_reference(today: date, count: int) -> str:
    """SMV-EU-YYYYMMDD-NNNN"""
    return f"SMV-EU-{today.strftime('%Y%m%d')}-{count + 1:04d}"


async def create_transaction(conn: asyncpg.Connection, data: dict) -> dict:
    today = date.today()
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM e_undiyal_transactions WHERE DATE(created_at) = $1",
        today,
    )
    reference = _generate_reference(today, count)

    row = await conn.fetchrow(
        """
        INSERT INTO e_undiyal_transactions (
            transaction_reference, user_id, donor_name, donor_phone,
            donor_email, amount_paise, donation_category,
            status, tax_certificate_eligible, certificate_status
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,'initiated',TRUE,'pending_details')
        RETURNING *
        """,
        reference,
        data.get("user_id"),
        data["donor_name"],
        data["donor_phone"],
        data.get("donor_email"),
        data["amount_paise"],
        data.get("donation_category"),
    )
    return dict(row)


async def get_transaction(conn: asyncpg.Connection, transaction_id: UUID) -> dict | None:
    row = await conn.fetchrow(
        "SELECT * FROM e_undiyal_transactions WHERE id = $1",
        str(transaction_id),
    )
    return dict(row) if row else None


async def get_transaction_by_reference(conn: asyncpg.Connection, reference: str) -> dict | None:
    row = await conn.fetchrow(
        "SELECT * FROM e_undiyal_transactions WHERE transaction_reference = $1",
        reference,
    )
    return dict(row) if row else None


async def update_status(conn: asyncpg.Connection, transaction_id: UUID, status: str) -> None:
    await conn.execute(
        "UPDATE e_undiyal_transactions SET status = $1, updated_at = NOW() WHERE id = $2",
        status, str(transaction_id),
    )


async def get_user_transactions(conn: asyncpg.Connection, user_id: str) -> list[dict]:
    rows = await conn.fetch(
        "SELECT * FROM e_undiyal_transactions WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    return [dict(r) for r in rows]
