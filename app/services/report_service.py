from datetime import date
from uuid import UUID
import asyncpg
from app.models.schemas.report import (
    DashboardKPIs, DailySummary, WeeklyTrend, MonthlyReport, 
    OccupancyReport, CertificateReport
)


async def get_dashboard_kpis(conn: asyncpg.Connection) -> DashboardKPIs:
    # Bookings today
    bookings = await conn.fetchrow("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed,
            COUNT(*) FILTER (WHERE status IN ('pending_payment', 'pending_approval')) as pending,
            COALESCE(SUM(amount_paise) FILTER (WHERE status = 'confirmed'), 0) as revenue
        FROM bookings
        WHERE DATE(created_at) = CURRENT_DATE
    """)

    # Active notices
    notices = await conn.fetchval("SELECT COUNT(*) FROM notices WHERE status = 'active'")

    # Slots nearing capacity
    slots = await conn.fetchval("""
        SELECT COUNT(*) FROM slot_inventory
        WHERE date >= CURRENT_DATE 
        AND total_capacity > 0 
        AND (confirmed_count::float / total_capacity::float) > 0.8
    """)

    # Pending approvals
    approvals = await conn.fetchval("SELECT COUNT(*) FROM bookings WHERE status = 'pending_approval'")

    # Pending certificates
    certificates = await conn.fetchval("SELECT COUNT(*) FROM e_undiyal_transactions WHERE certificate_status = 'processing'")

    # E-Undiyal today
    undiyal = await conn.fetchrow("""
        SELECT COUNT(*) as count, COALESCE(SUM(amount_paise), 0) as amount
        FROM e_undiyal_transactions
        WHERE DATE(created_at) = CURRENT_DATE AND status = 'success'
    """)

    return DashboardKPIs(
        bookings_today=bookings["total"],
        confirmed_bookings_today=bookings["confirmed"],
        pending_bookings_today=bookings["pending"],
        revenue_today=bookings["revenue"],
        active_notices=notices,
        slots_nearing_capacity=slots,
        pending_approvals=approvals,
        pending_certificates=certificates,
        e_undiyal_count_today=undiyal["count"],
        e_undiyal_amount_today=undiyal["amount"]
    )


async def get_daily_summary(conn: asyncpg.Connection, target_date: date) -> DailySummary:
    status_counts = await conn.fetch("""
        SELECT status, COUNT(*) FROM bookings WHERE DATE(booking_date) = $1 GROUP BY status
    """, target_date)
    
    revenue = await conn.fetchval("SELECT COALESCE(SUM(amount_paise), 0) FROM bookings WHERE DATE(booking_date) = $1 AND status = 'confirmed'", target_date)
    
    service_counts = await conn.fetch("""
        SELECT s.name, COUNT(b.id) 
        FROM bookings b JOIN services s ON b.service_id = s.id 
        WHERE DATE(b.booking_date) = $1 GROUP BY s.name
    """, target_date)
    
    undiyal = await conn.fetchrow("""
        SELECT COUNT(*) as count, COALESCE(SUM(amount_paise), 0) as amount
        FROM e_undiyal_transactions
        WHERE DATE(created_at) = $1 AND status = 'success'
    """, target_date)
    
    conflicts = await conn.fetchval("""
        SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'conflict.%' AND DATE(created_at) = $1
    """, target_date)

    return DailySummary(
        date=target_date,
        bookings_by_status={row["status"]: row["count"] for row in status_counts},
        total_revenue=revenue,
        bookings_per_service={row["name"]: row["count"] for row in service_counts},
        e_undiyal_count=undiyal["count"],
        e_undiyal_amount=undiyal["amount"],
        conflict_events=conflicts
    )


async def get_weekly_trend(conn: asyncpg.Connection, start_date: date, end_date: date) -> WeeklyTrend:
    daily_vols = await conn.fetch("""
        SELECT DATE(booking_date) as d, COUNT(*) as c FROM bookings 
        WHERE booking_date >= $1 AND booking_date <= $2 
        GROUP BY DATE(booking_date)
    """, start_date, end_date)
    
    daily_revs = await conn.fetch("""
        SELECT DATE(booking_date) as d, COALESCE(SUM(amount_paise), 0) as r FROM bookings 
        WHERE booking_date >= $1 AND booking_date <= $2 AND status = 'confirmed' 
        GROUP BY DATE(booking_date)
    """, start_date, end_date)
    
    occupancy = await conn.fetch("""
        SELECT DATE(date) as d, AVG(CASE WHEN total_capacity > 0 THEN confirmed_count::float / total_capacity ELSE 0 END) as occ
        FROM slot_inventory
        WHERE date >= $1 AND date <= $2
        GROUP BY DATE(date)
    """, start_date, end_date)

    return WeeklyTrend(
        start_date=start_date,
        end_date=end_date,
        daily_volumes={str(row["d"]): row["c"] for row in daily_vols},
        daily_revenue={str(row["d"]): row["r"] for row in daily_revs},
        occupancy_rates={str(row["d"]): float(row["occ"]) for row in occupancy}
    )


async def get_monthly_report(conn: asyncpg.Connection, year: int, month: int) -> MonthlyReport:
    # Need proper date math or EXTRACT logic
    rev = await conn.fetchrow("""
        SELECT 
            COALESCE(SUM(amount_paise), 0) as gross,
            COALESCE(SUM(amount_paise) FILTER (WHERE status = 'confirmed'), 0) as net
        FROM payments
        WHERE EXTRACT(YEAR FROM created_at) = $1 AND EXTRACT(MONTH FROM created_at) = $2
    """, year, month)
    
    services = await conn.fetch("""
        SELECT s.name, COUNT(b.id) as count 
        FROM bookings b JOIN services s ON b.service_id = s.id 
        WHERE EXTRACT(YEAR FROM b.booking_date) = $1 AND EXTRACT(MONTH FROM b.booking_date) = $2
        GROUP BY s.name ORDER BY count DESC
    """, year, month)
    
    users = await conn.fetchval("""
        SELECT COUNT(*) FROM users 
        WHERE EXTRACT(YEAR FROM created_at) = $1 AND EXTRACT(MONTH FROM created_at) = $2
    """, year, month)
    
    undiyal = await conn.fetchrow("""
        SELECT COUNT(*) as count, COALESCE(SUM(amount_paise), 0) as amount
        FROM e_undiyal_transactions
        WHERE status = 'success' AND EXTRACT(YEAR FROM created_at) = $1 AND EXTRACT(MONTH FROM created_at) = $2
    """, year, month)

    return MonthlyReport(
        year=year,
        month=month,
        gross_revenue=rev["gross"],
        net_revenue=rev["net"],
        service_performance=[{"name": row["name"], "count": row["count"]} for row in services],
        new_users=users,
        e_undiyal_count=undiyal["count"],
        e_undiyal_total=undiyal["amount"]
    )


async def get_service_occupancy(conn: asyncpg.Connection, service_id: UUID, start_date: date, end_date: date) -> OccupancyReport:
    rows = await conn.fetch("""
        SELECT date, session, total_capacity, confirmed_count
        FROM slot_inventory
        WHERE service_id = $1 AND date >= $2 AND date <= $3
        ORDER BY date ASC
    """, str(service_id), start_date, end_date)
    
    daily = []
    total_cap = 0
    total_conf = 0
    for r in rows:
        daily.append({
            "date": str(r["date"]),
            "session": r["session"],
            "capacity": r["total_capacity"],
            "confirmed": r["confirmed_count"]
        })
        total_cap += r["total_capacity"]
        total_conf += r["confirmed_count"]
        
    avg_occ = (total_conf / total_cap) * 100 if total_cap > 0 else 0.0

    return OccupancyReport(
        service_id=str(service_id),
        start_date=start_date,
        end_date=end_date,
        daily_occupancy=daily,
        average_occupancy_percentage=avg_occ
    )


async def get_certificate_report(conn: asyncpg.Connection, start_date: date | None, end_date: date | None) -> CertificateReport:
    query = "SELECT certificate_status as status, donor_location_type as loc, COUNT(*) as count FROM e_undiyal_transactions WHERE certificate_status IS NOT NULL"
    args = []
    if start_date:
        query += f" AND DATE(created_at) >= ${len(args) + 1}"
        args.append(start_date)
    if end_date:
        query += f" AND DATE(created_at) <= ${len(args) + 1}"
        args.append(end_date)
        
    query += " GROUP BY certificate_status, donor_location_type"
    rows = await conn.fetch(query, *args)
    
    status_counts = {}
    international = 0
    domestic = 0
    for r in rows:
        s = r["status"]
        status_counts[s] = status_counts.get(s, 0) + r["count"]
        if r["loc"] == "international":
            international += r["count"]
        elif r["loc"] in ("domestic", "local"):
            domestic += r["count"]
            
    return CertificateReport(
        start_date=start_date,
        end_date=end_date,
        certificates_by_status=status_counts,
        international_count=international,
        domestic_count=domestic
    )


async def get_audit_logs(conn: asyncpg.Connection, action: str | None, start: date | None, end: date | None, page: int = 1) -> list[dict]:
    limit = 1000
    offset = (page - 1) * limit
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    args = []
    if action:
        query += f" AND action = ${len(args) + 1}"
        args.append(action)
    if start:
        query += f" AND DATE(created_at) >= ${len(args) + 1}"
        args.append(start)
    if end:
        query += f" AND DATE(created_at) <= ${len(args) + 1}"
        args.append(end)
        
    query += f" ORDER BY created_at DESC LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}"
    args.extend([limit, offset])
    
    rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]
