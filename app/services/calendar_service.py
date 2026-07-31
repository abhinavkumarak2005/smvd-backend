import json
from datetime import date
from uuid import UUID
import asyncpg
from pydantic import BaseModel


class DateStatus(BaseModel):
    status: str
    notes: str | None = None


async def check_date(conn: asyncpg.Connection, target_date: date, service_id: UUID) -> DateStatus:
    row = await conn.fetchrow("SELECT * FROM calendar_dates WHERE date = $1", target_date)
    if not row:
        return DateStatus(status="open")
        
    if row["status"] == "blocked":
        return DateStatus(status="blocked", notes=row["notes"])
        
    if row["status"] == "partial":
        allowed = json.loads(row["allowed_service_ids"]) if row["allowed_service_ids"] else []
        if str(service_id) in allowed:
            return DateStatus(status="open")
        return DateStatus(status="blocked", notes=row["notes"])
        
    return DateStatus(status="open")
