from uuid import UUID
import asyncpg


async def create_payment_record(
    conn: asyncpg.Connection, booking_id: UUID | None = None, gateway_order_id: str = "", amount_paise: int = 0, e_undiyal_id: UUID | None = None
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO payments (booking_id, gateway_order_id, amount_paise, status, currency, e_undiyal_id)
        VALUES ($1, $2, $3, 'initiated', 'INR', $4)
        RETURNING *
        """,
        str(booking_id) if booking_id else None, gateway_order_id, amount_paise, str(e_undiyal_id) if e_undiyal_id else None
    )
    return dict(row)

async def update_payment_status(
    conn: asyncpg.Connection, gateway_order_id: str, status: str, gateway_payment_id: str | None = None
) -> None:
    if gateway_payment_id:
        await conn.execute(
            "UPDATE payments SET status = $1, gateway_payment_id = $2, paid_at = NOW(), updated_at = NOW() WHERE gateway_order_id = $3",
            status, gateway_payment_id, gateway_order_id
        )
    else:
        await conn.execute(
            "UPDATE payments SET status = $1, updated_at = NOW() WHERE gateway_order_id = $2",
            status, gateway_order_id
        )

async def get_payment_by_order_id(conn: asyncpg.Connection, gateway_order_id: str) -> dict | None:
    row = await conn.fetchrow("SELECT * FROM payments WHERE gateway_order_id = $1", gateway_order_id)
    return dict(row) if row else None
