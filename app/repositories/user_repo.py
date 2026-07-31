from uuid import UUID
import asyncpg


async def get_user(conn: asyncpg.Connection, user_id: UUID) -> dict | None:
    row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user_id))
    return dict(row) if row else None


async def get_all_users(conn: asyncpg.Connection, page: int, limit: int, role_filter: str | None) -> list[dict]:
    offset = (page - 1) * limit
    query = "SELECT * FROM users"
    args: list = []
    if role_filter:
        query += " WHERE role = $1"
        args.append(role_filter)
        
    query += f" ORDER BY created_at DESC LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}"
    args.extend([limit, offset])
    
    rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]


async def search_users(conn: asyncpg.Connection, query: str) -> list[dict]:
    pattern = f"%{query}%"
    rows = await conn.fetch(
        "SELECT * FROM users WHERE phone ILIKE $1 OR email ILIKE $1 OR full_name ILIKE $1 ORDER BY created_at DESC",
        pattern
    )
    return [dict(r) for r in rows]


async def update_user_role(conn: asyncpg.Connection, user_id: UUID, role: str) -> None:
    await conn.execute("UPDATE users SET role = $1, updated_at = NOW() WHERE id = $2", role, str(user_id))


async def deactivate_user(conn: asyncpg.Connection, user_id: UUID) -> None:
    await conn.execute("UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = $1", str(user_id))


async def get_user_booking_summary(conn: asyncpg.Connection, user_id: UUID) -> dict:
    row = await conn.fetchrow(
        "SELECT COUNT(*) as booking_count, COALESCE(SUM(amount_paise), 0) as booking_total FROM bookings WHERE user_id = $1",
        str(user_id)
    )
    return dict(row)

async def get_user_donation_summary(conn: asyncpg.Connection, user_id: UUID) -> dict:
    row = await conn.fetchrow(
        "SELECT COUNT(*) as donation_count, COALESCE(SUM(amount_paise), 0) as donation_total FROM e_undiyal_transactions WHERE user_id = $1 AND status = 'success'",
        str(user_id)
    )
    return dict(row)
