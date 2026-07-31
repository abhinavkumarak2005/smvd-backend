from datetime import date
from uuid import UUID
import asyncpg


async def get_inventory(
    conn: asyncpg.Connection,
    service_id: UUID,
    start_date: date,
    end_date: date,
) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT 
            id, date, session, total_capacity, confirmed_count, 
            pending_count, is_blocked, block_reason, created_at, updated_at,
            (total_capacity - confirmed_count - pending_count) as available
        FROM slot_inventory 
        WHERE service_id = $1 AND date >= $2 AND date <= $3
        ORDER BY date ASC, session ASC
        """,
        str(service_id), start_date, end_date
    )
    return [dict(r) for r in rows]


async def block_slot(conn: asyncpg.Connection, slot_id: UUID, reason: str) -> None:
    await conn.execute(
        "UPDATE slot_inventory SET is_blocked = TRUE, block_reason = $1, updated_at = NOW() WHERE id = $2",
        reason, str(slot_id)
    )


async def update_capacity(conn: asyncpg.Connection, slot_id: UUID, total_capacity: int) -> None:
    await conn.execute(
        "UPDATE slot_inventory SET total_capacity = $1, updated_at = NOW() WHERE id = $2",
        total_capacity, str(slot_id)
    )


async def release_slot(conn: asyncpg.Connection, booking_id: UUID) -> None:
    """Decrease confirmed_count or pending_count based on rejected/cancelled booking."""
    # Find the slot info from the booking
    booking = await conn.fetchrow("SELECT slot_id, status FROM bookings WHERE id = $1", str(booking_id))
    if not booking:
        return
        
    slot_id = booking["slot_id"]
    if booking["status"] in ("pending_payment", "pending_approval"):
        await conn.execute("UPDATE slot_inventory SET pending_count = GREATEST(pending_count - 1, 0) WHERE id = $1", slot_id)
    else:
        await conn.execute("UPDATE slot_inventory SET confirmed_count = GREATEST(confirmed_count - 1, 0) WHERE id = $1", slot_id)


async def get_slot_for_update(conn: asyncpg.Connection, service_id: UUID, target_date: date, session: str) -> dict | None:
    row = await conn.fetchrow(
        "SELECT * FROM slot_inventory WHERE service_id = $1 AND date = $2 AND session = $3 FOR UPDATE",
        str(service_id), target_date, session
    )
    return dict(row) if row else None


async def get_or_create_slot(conn: asyncpg.Connection, service_id: UUID, target_date: date, session: str, capacity: int) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO slot_inventory (service_id, date, session, total_capacity)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (service_id, date, session) DO UPDATE 
        SET updated_at = NOW()
        RETURNING *
        """,
        str(service_id), target_date, session, capacity
    )
    return dict(row)


async def increment_pending(conn: asyncpg.Connection, slot_id: UUID) -> None:
    await conn.execute("UPDATE slot_inventory SET pending_count = pending_count + 1, updated_at = NOW() WHERE id = $1", str(slot_id))


async def decrement_pending(conn: asyncpg.Connection, slot_id: UUID) -> None:
    await conn.execute("UPDATE slot_inventory SET pending_count = GREATEST(pending_count - 1, 0), updated_at = NOW() WHERE id = $1", str(slot_id))


async def confirm_slot(conn: asyncpg.Connection, slot_id: UUID) -> None:
    await conn.execute(
        "UPDATE slot_inventory SET confirmed_count = confirmed_count + 1, pending_count = GREATEST(pending_count - 1, 0), updated_at = NOW() WHERE id = $1", 
        str(slot_id)
    )
