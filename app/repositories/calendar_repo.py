import json
from datetime import date
from uuid import UUID
import asyncpg


async def get_date(conn: asyncpg.Connection, target_date: date) -> dict | None:
    row = await conn.fetchrow(
        "SELECT * FROM calendar_dates WHERE date = $1",
        target_date
    )
    if not row:
        return None
    d = dict(row)
    if d.get("allowed_service_ids"):
        d["allowed_service_ids"] = json.loads(d["allowed_service_ids"])
    else:
        d["allowed_service_ids"] = []
    return d


async def upsert_date(
    conn: asyncpg.Connection,
    target_date: date,
    status: str,
    allowed_service_ids: list[UUID],
    notes: str | None = None,
    notes_tamil: str | None = None,
    created_by: UUID | None = None
) -> dict:
    allowed_json = json.dumps([str(sid) for sid in allowed_service_ids])
    
    row = await conn.fetchrow(
        """
        INSERT INTO calendar_dates (date, status, allowed_service_ids, notes, notes_tamil, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (date) DO UPDATE SET
            status = EXCLUDED.status,
            allowed_service_ids = EXCLUDED.allowed_service_ids,
            notes = EXCLUDED.notes,
            notes_tamil = EXCLUDED.notes_tamil,
            updated_at = NOW()
        RETURNING *
        """,
        target_date, status, allowed_json, notes, notes_tamil, str(created_by) if created_by else None
    )
    d = dict(row)
    d["allowed_service_ids"] = json.loads(d["allowed_service_ids"])
    return d


async def delete_date(conn: asyncpg.Connection, target_date: date) -> None:
    await conn.execute("DELETE FROM calendar_dates WHERE date = $1", target_date)


async def get_date_range(conn: asyncpg.Connection, start_date: date, end_date: date) -> list[dict]:
    rows = await conn.fetch(
        "SELECT * FROM calendar_dates WHERE date BETWEEN $1 AND $2 ORDER BY date ASC",
        start_date, end_date
    )
    res = []
    for r in rows:
        d = dict(r)
        d["allowed_service_ids"] = json.loads(d["allowed_service_ids"]) if d.get("allowed_service_ids") else []
        res.append(d)
    return res
