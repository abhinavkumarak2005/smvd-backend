from uuid import UUID
import asyncpg


async def get_active_notices(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT * FROM notices
        WHERE status = 'active'
          AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY priority DESC, published_at DESC
        """
    )
    return [dict(r) for r in rows]


async def get_all_notices(conn: asyncpg.Connection, status_filter: str | None, page: int = 1, limit: int = 20) -> list[dict]:
    query = "SELECT * FROM notices WHERE 1=1"
    args = []
    if status_filter:
        args.append(status_filter)
        query += f" AND status = ${len(args)}"
    
    offset = (page - 1) * limit
    args.extend([limit, offset])
    query += f" ORDER BY created_at DESC LIMIT ${len(args) - 1} OFFSET ${len(args)}"
    
    rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]


async def get_notice(conn: asyncpg.Connection, notice_id: UUID) -> dict | None:
    row = await conn.fetchrow("SELECT * FROM notices WHERE id = $1", str(notice_id))
    return dict(row) if row else None


async def create_notice(conn: asyncpg.Connection, data: dict) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO notices (
            title, title_tamil, body, body_tamil, category,
            priority, status, published_at, expires_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, COALESCE($8, NOW()), $9)
        RETURNING *
        """,
        data["title"],
        data.get("title_tamil"),
        data["body"],
        data.get("body_tamil"),
        data.get("category"),
        data.get("priority", 0),
        data.get("status", "draft"),
        data.get("published_at"),
        data.get("expires_at"),
    )
    return dict(row)


async def update_notice(conn: asyncpg.Connection, notice_id: UUID, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return await get_notice(conn, notice_id)

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
    values = list(fields.values())
    
    row = await conn.fetchrow(
        f"UPDATE notices SET {set_clause}, updated_at = NOW() WHERE id = $1 RETURNING *",
        str(notice_id), *values
    )
    return dict(row) if row else None


async def activate_notice(conn: asyncpg.Connection, notice_id: UUID) -> None:
    await conn.execute("UPDATE notices SET status = 'active', updated_at = NOW() WHERE id = $1", str(notice_id))


async def deactivate_notice(conn: asyncpg.Connection, notice_id: UUID) -> None:
    await conn.execute("UPDATE notices SET status = 'expired', updated_at = NOW() WHERE id = $1", str(notice_id))


async def delete_notice(conn: asyncpg.Connection, notice_id: UUID) -> None:
    await conn.execute("UPDATE notices SET status = 'expired', updated_at = NOW() WHERE id = $1", str(notice_id))


async def activate_scheduled(conn: asyncpg.Connection) -> int:
    result = await conn.execute(
        "UPDATE notices SET status = 'active', updated_at = NOW() WHERE status = 'scheduled' AND published_at <= NOW()"
    )
    return int(result.split(" ")[1])


async def expire_old(conn: asyncpg.Connection) -> int:
    result = await conn.execute(
        "UPDATE notices SET status = 'expired', updated_at = NOW() WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at < NOW()"
    )
    return int(result.split(" ")[1])
