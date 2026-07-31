from datetime import date
from uuid import UUID
import asyncpg
from pydantic import BaseModel

class ConflictResult(BaseModel):
    blocked: bool
    requires_approval: bool
    message: str | None = None
    notice: str | None = None

from app.repositories import conflict_repo

async def _has_booking_for_service(conn: asyncpg.Connection, s_id: UUID, d: date, status_in: tuple = ('confirmed', 'pending_payment', 'pending_approval')) -> bool:
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM bookings WHERE service_id = $1 AND booking_date = $2 AND status = ANY($3::text[])",
        str(s_id), d, list(status_in)
    )
    return count > 0

async def check_conflicts(conn: asyncpg.Connection, service_id: UUID, target_date: date, session: str) -> ConflictResult:
    rules = await conflict_repo.get_rules_for_service(conn, service_id)
    
    requires_approval = False
    notice = None
    
    for rule in rules:
        service_a = UUID(rule["service_a_id"])
        service_b = UUID(rule["service_b_id"])
        
        # Determine the "other" service
        other_service_id = service_b if service_a == service_id else service_a
        
        if rule["rule_type"] == "mutual_exclusion":
            if await _has_booking_for_service(conn, other_service_id, target_date):
                return ConflictResult(blocked=True, requires_approval=False, message=rule["notice_text"])
                
        elif rule["rule_type"] == "a_blocks_b":
            # If we are booking service_b, check if service_a has a booking
            if service_id == service_b:
                if await _has_booking_for_service(conn, service_a, target_date):
                    return ConflictResult(blocked=True, requires_approval=False, message=rule["notice_text"])
                    
        elif rule["rule_type"] == "requires_approval":
            # If we are booking service_b, check if service_a has a booking
            # (or potentially bidirectional if direction='bidirectional', but requirement says a_to_b typically)
            if rule["direction"] == "bidirectional" or service_id == service_b:
                if await _has_booking_for_service(conn, other_service_id, target_date):
                    requires_approval = True
                    notice = rule["notice_text"]
                    
    return ConflictResult(blocked=False, requires_approval=requires_approval, notice=notice)
