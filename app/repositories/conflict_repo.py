from uuid import UUID
import asyncpg


async def get_rules_for_service(conn: asyncpg.Connection, service_id: UUID) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT * FROM conflict_rules
        WHERE (service_a_id = $1 OR service_b_id = $1)
        AND is_active = true
        """,
        str(service_id)
    )
    return [dict(r) for r in rows]
