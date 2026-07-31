from datetime import date
from typing import Dict
from pydantic import BaseModel


class DashboardKPIs(BaseModel):
    bookings_today: int
    confirmed_bookings_today: int
    pending_bookings_today: int
    revenue_today: int
    active_notices: int
    slots_nearing_capacity: int
    pending_approvals: int
    pending_certificates: int
    e_undiyal_count_today: int
    e_undiyal_amount_today: int


class DailySummary(BaseModel):
    date: date
    bookings_by_status: dict[str, int]
    total_revenue: int
    bookings_per_service: dict[str, int]
    e_undiyal_count: int
    e_undiyal_amount: int
    conflict_events: int


class WeeklyTrend(BaseModel):
    start_date: date
    end_date: date
    daily_volumes: dict[str, int]
    daily_revenue: dict[str, int]
    occupancy_rates: dict[str, float]


class MonthlyReport(BaseModel):
    year: int
    month: int
    gross_revenue: int
    net_revenue: int
    service_performance: list[dict]
    new_users: int
    e_undiyal_count: int
    e_undiyal_total: int


class OccupancyReport(BaseModel):
    service_id: str
    start_date: date
    end_date: date
    daily_occupancy: list[dict]
    average_occupancy_percentage: float


class CertificateReport(BaseModel):
    start_date: date | None
    end_date: date | None
    certificates_by_status: dict[str, int]
    international_count: int
    domestic_count: int
