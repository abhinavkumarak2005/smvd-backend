import logging
from app.database import get_db_pool
from app.repositories import slot_inventory_repo
from app.services import audit_service

logger = logging.getLogger(__name__)

async def cleanup_expired_bookings():
    """
    Run every 5 minutes to sweep pending_payment bookings that are > 15 minutes old.
    Mark them as expired, decrement the slot pending_count, and log it.
    """
    pool = get_db_pool()
    if not pool:
        return
        
    async with pool.acquire() as conn:
        # 1. Fetch expired bookings
        # We process them in chunks of 100 to avoid long locks
        expired_bookings = await conn.fetch(
            """
            SELECT id, slot_id, user_id 
            FROM bookings 
            WHERE status = 'pending_payment' 
              AND created_at < NOW() - INTERVAL '15 minutes'
            LIMIT 100
            """
        )
        
        if not expired_bookings:
            return
            
        cleaned_count = 0
        
        for b in expired_bookings:
            # 2. Process each booking transactionally
            async with conn.transaction():
                # Lock the slot
                await conn.fetchrow("SELECT id FROM slot_inventory WHERE id = $1 FOR UPDATE", b["slot_id"])
                
                # Decrement pending count
                await slot_inventory_repo.decrement_pending(conn, b["slot_id"])
                
                # Update booking
                await conn.execute(
                    "UPDATE bookings SET status = 'expired', updated_at = NOW() WHERE id = $1", 
                    b["id"]
                )
                
                # Update payments if any exist
                await conn.execute(
                    "UPDATE payments SET status = 'expired', updated_at = NOW() WHERE booking_id = $1 AND status = 'initiated'",
                    b["id"]
                )
                
                # Audit log
                await audit_service.write_log(
                    action="booking.expired",
                    target_id=str(b["id"]),
                    user_id=b["user_id"],
                    new_values={"status": "expired"}
                )
                
                cleaned_count += 1
                
        logger.info("Cleaned up %d expired pending bookings", cleaned_count)
