import pytest
from uuid import uuid4
from datetime import date
from unittest.mock import patch
from app.models.schemas.report import DashboardKPIs, DailySummary, OccupancyReport

@pytest.fixture
def staff_client(client):
    from app.dependencies.auth import get_current_user, CurrentUser
    from app.main import app
    
    async def override_get_current_user():
        return CurrentUser(id=str(uuid4()), role="staff")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()

@pytest.mark.asyncio
@patch("app.routers.admin.reports.report_service.get_dashboard_kpis")
async def test_dashboard_kpis(mock_get_kpis, staff_client):
    mock_get_kpis.return_value = DashboardKPIs(
        bookings_today=10,
        confirmed_bookings_today=8,
        pending_bookings_today=2,
        revenue_today=100000,
        active_notices=1,
        slots_nearing_capacity=0,
        pending_approvals=2,
        pending_certificates=5,
        e_undiyal_count_today=20,
        e_undiyal_amount_today=50000
    )
    
    response = staff_client.get("/api/v1/admin/reports/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["bookings_today"] == 10
    assert data["revenue_today"] == 100000
    assert data["e_undiyal_count_today"] == 20

@pytest.mark.asyncio
@patch("app.routers.admin.reports.report_service.get_daily_summary")
async def test_daily_report(mock_get_daily, staff_client):
    report_date = date(2026, 10, 10)
    mock_get_daily.return_value = DailySummary(
        date=report_date,
        bookings_by_status={"approved": 5, "pending_payment": 1},
        total_revenue=50000,
        bookings_per_service={"General": 6},
        e_undiyal_count=10,
        e_undiyal_amount=20000,
        conflict_events=0
    )
    
    response = staff_client.get("/api/v1/admin/reports/daily?date=2026-10-10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == 50000
    assert data["bookings_by_status"]["approved"] == 5

@pytest.mark.asyncio
@patch("app.routers.admin.reports.report_service.get_service_occupancy")
async def test_occupancy_no_bookings(mock_get_occupancy, staff_client):
    service_id = str(uuid4())
    mock_get_occupancy.return_value = OccupancyReport(
        service_id=service_id,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        daily_occupancy=[],
        average_occupancy_percentage=0.0 # Testing the 0% requirement
    )
    
    response = staff_client.get(f"/api/v1/admin/reports/occupancy?service_id={service_id}&start=2026-10-01&end=2026-10-31")
    assert response.status_code == 200
    data = response.json()
    assert data["average_occupancy_percentage"] == 0.0
