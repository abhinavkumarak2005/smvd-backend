from datetime import date
from uuid import UUID
import asyncpg


async def get_all_bookings(
    conn: asyncpg.Connection,
    status: str | None = None,
    booking_date: date | None = None,
    service_id: UUID | None = None,
    page: int = 1,
    limit: int = 20,
) -> list[dict]:
    offset = (page - 1) * limit
    query = "SELECT b.*, s.name as service_name, u.full_name as user_name FROM bookings b JOIN services s ON b.service_id = s.id LEFT JOIN users u ON b.user_id = u.id WHERE 1=1"
    args: list = []
    
    if status:
        query += f" AND b.status = ${len(args) + 1}"
        args.append(status)
    if booking_date:
        query += f" AND b.booking_date = ${len(args) + 1}"
        args.append(booking_date)
    if service_id:
        query += f" AND b.service_id = ${len(args) + 1}"
        args.append(str(service_id))
        
    query += f" ORDER BY b.created_at DESC LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}"
    args.extend([limit, offset])
    
    rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]


async def get_booking(conn: asyncpg.Connection, booking_id: UUID) -> dict | None:
    row = await conn.fetchrow(
        "SELECT b.*, s.name as service_name FROM bookings b JOIN services s ON b.service_id = s.id WHERE b.id = $1",
        str(booking_id)
    )
    if not row:
        return None
        
    booking = dict(row)
    # Get persons
    persons = await conn.fetch("SELECT * FROM booking_persons WHERE booking_id = $1", str(booking_id))
    booking["persons"] = [dict(p) for p in persons]
    
    # Get payment info
    payment = await conn.fetchrow("SELECT * FROM payments WHERE booking_id = $1", str(booking_id))
    booking["payment"] = dict(payment) if payment else None
    
    return booking


async def update_status(
    conn: asyncpg.Connection,
    booking_id: UUID,
    status: str,
    admin_id: UUID | None = None,
    approval_note: str | None = None,
) -> None:
    if status == "approved":
        await conn.execute(
            "UPDATE bookings SET status = $1, approved_by = $2, approved_at = NOW(), approval_note = $3, updated_at = NOW() WHERE id = $4",
            status, str(admin_id), approval_note, str(booking_id)
        )
    else:
        await conn.execute(
            "UPDATE bookings SET status = $1, updated_at = NOW() WHERE id = $2",
            status, str(booking_id)
        )


async def get_pending_approvals(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        "SELECT b.*, s.name as service_name FROM bookings b JOIN services s ON b.service_id = s.id WHERE b.status = 'pending_approval' ORDER BY b.created_at ASC"
    )
    return [dict(r) for r in rows]

async def check_duplicate(conn: asyncpg.Connection, user_id: UUID, service_id: UUID, target_date: date, session: str) -> bool:
    count = await conn.fetchval(
        """
        SELECT COUNT(*) FROM bookings 
        WHERE user_id = $1 AND service_id = $2 AND booking_date = $3 AND session = $4 
        AND status IN ('confirmed', 'pending_payment', 'pending_approval')
        """,
        str(user_id), str(service_id), target_date, session
    )
    return count > 0

async def get_user_bookings(conn: asyncpg.Connection, user_id: UUID, page: int = 1, limit: int = 20) -> list[dict]:
    offset = (page - 1) * limit
    rows = await conn.fetch(
        """
        SELECT b.*, s.name as service_name 
        FROM bookings b JOIN services s ON b.service_id = s.id 
        WHERE b.user_id = $1 
        ORDER BY b.created_at DESC 
        LIMIT $2 OFFSET $3
        """,
        str(user_id), limit, offset
    )
    return [dict(r) for r in rows]

async def create_booking(conn: asyncpg.Connection, data: dict) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO bookings (
            user_id, service_id, booking_date, session, slot_id, 
            status, reference_number, notes, amount_paise, requires_approval
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
        """,
        data["user_id"], data["service_id"], data["booking_date"], data["session"], 
        data["slot_id"], data["status"], data["reference_number"], 
        data.get("notes"), data["amount_paise"], data.get("requires_approval", False)
    )
    return dict(row)

async def insert_persons(conn: asyncpg.Connection, booking_id: UUID, persons: list[dict]) -> None:
    for p in persons:
        await conn.execute(
            """
            INSERT INTO booking_persons (booking_id, full_name, age, gender, nakshatram, gothram)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            str(booking_id), p["full_name"], p.get("age"), p.get("gender"), 
            p.get("star") or p.get("nakshatram"), p.get("gothram")
        )
