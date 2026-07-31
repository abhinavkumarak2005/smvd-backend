from uuid import UUID
from typing import Any
import asyncpg

from app.database import get_db
from fastapi import Depends


class ServiceRepo:

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_all_services(self, active_only: bool = True) -> list[dict]:
        query = "SELECT * FROM services"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY sort_order"
        rows = await self.conn.fetch(query)
        return [dict(r) for r in rows]

    async def get_service(self, service_id: UUID) -> dict | None:
        row = await self.conn.fetchrow(
            "SELECT * FROM services WHERE id = $1", str(service_id)
        )
        return dict(row) if row else None

    async def create_service(self, data: dict) -> dict:
        row = await self.conn.fetchrow(
            """
            INSERT INTO services (
                name, name_tamil, category, description, description_tamil,
                price_paise, max_persons, advance_booking_days, session,
                image_url, sort_order
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING *
            """,
            data["name"], data.get("name_tamil"), data.get("category"),
            data.get("description"), data.get("description_tamil"),
            data["price_paise"], data.get("max_persons", 5),
            data.get("advance_booking_days", 1), data.get("session", "na"),
            data.get("image_url"), data.get("sort_order", 0),
        )
        return dict(row)

    async def update_service(self, service_id: UUID, data: dict) -> dict | None:
        # Build dynamic SET clause from non-None fields
        fields = {k: v for k, v in data.items() if v is not None}
        if not fields:
            return await self.get_service(service_id)
        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        values = list(fields.values())
        row = await self.conn.fetchrow(
            f"UPDATE services SET {set_clause}, updated_at = NOW() "
            f"WHERE id = $1 RETURNING *",
            str(service_id), *values,
        )
        return dict(row) if row else None

    async def toggle_active(self, service_id: UUID, is_active: bool) -> None:
        await self.conn.execute(
            "UPDATE services SET is_active = $1, updated_at = NOW() WHERE id = $2",
            is_active, str(service_id),
        )


def get_service_repo(conn: asyncpg.Connection = Depends(get_db)) -> ServiceRepo:
    return ServiceRepo(conn)
