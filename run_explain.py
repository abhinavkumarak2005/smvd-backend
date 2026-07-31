import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

queries = {
    "Dashboard Bookings Today": """
        EXPLAIN ANALYZE
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed,
            COUNT(*) FILTER (WHERE status IN ('pending_payment', 'pending_approval')) as pending,
            COALESCE(SUM(amount_paise) FILTER (WHERE status = 'confirmed'), 0) as revenue
        FROM bookings
        WHERE DATE(created_at) = CURRENT_DATE
    """,
    "Monthly Revenue": """
        EXPLAIN ANALYZE
        SELECT 
            COALESCE(SUM(amount_paise), 0) as gross,
            COALESCE(SUM(amount_paise) FILTER (WHERE status = 'confirmed'), 0) as net
        FROM payments
        WHERE EXTRACT(YEAR FROM created_at) = 2026 AND EXTRACT(MONTH FROM created_at) = 8
    """,
    "Search Users": """
        EXPLAIN ANALYZE
        SELECT * FROM users 
        WHERE phone ILIKE '%999%' OR email ILIKE '%999%' OR full_name ILIKE '%999%'
    """,
    "List Pending Certificates": """
        EXPLAIN ANALYZE
        SELECT * FROM e_undiyal_transactions 
        WHERE certificate_status = 'processing' 
        ORDER BY created_at ASC 
        LIMIT 20 OFFSET 0
    """,
    "Audit Logs Filter": """
        EXPLAIN ANALYZE
        SELECT * FROM audit_logs 
        WHERE action = 'booking.created' 
        ORDER BY created_at DESC 
        LIMIT 20 OFFSET 0
    """
}

async def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return
        
    conn = await asyncpg.connect(db_url)
    try:
        for name, query in queries.items():
            print(f"--- {name} ---")
            results = await conn.fetch(query)
            for r in results:
                print(r[0])
            print("\n")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
