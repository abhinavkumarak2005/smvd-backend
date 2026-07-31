import pytest
from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user, CurrentUser

@pytest.fixture
def staff_client(client):
    async def override_get_current_user():
        return CurrentUser(id=str(uuid4()), role="staff")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def standard_admin_client(client):
    async def override_get_current_user():
        return CurrentUser(id=str(uuid4()), role="admin")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_devotee_on_admin_bookings(auth_client):
    response = auth_client.get("/api/v1/admin/bookings")
    assert response.status_code == 403

@pytest.mark.asyncio
@patch("app.routers.admin.reports.report_service.get_dashboard_kpis")
async def test_staff_on_dashboard(mock_get_kpis, staff_client, mock_conn):
    from app.models.schemas.report import DashboardKPIs
    mock_get_kpis.return_value = DashboardKPIs(
        bookings_today=0, confirmed_bookings_today=0, pending_bookings_today=0,
        revenue_today=0, active_notices=0, slots_nearing_capacity=0,
        pending_approvals=0, pending_certificates=0, e_undiyal_count_today=0,
        e_undiyal_amount_today=0
    )
    response = staff_client.get("/api/v1/admin/reports/dashboard")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_staff_on_approve_booking(staff_client):
    response = staff_client.post(f"/api/v1/admin/bookings/{uuid4()}/approve", json={"note": "ok"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_admin_on_approve_booking(standard_admin_client, mock_conn):
    booking_id = uuid4()
    mock_conn.fetchrow.return_value = {
        "id": booking_id,
        "status": "pending_approval",
        "phone": "+919999999999"
    }
    response = standard_admin_client.post(f"/api/v1/admin/bookings/{booking_id}/approve", json={"note": "ok"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_admin_on_create_service(standard_admin_client):
    req_body = {
        "name": "Test Service",
        "price_paise": 1000
    }
    response = standard_admin_client.post("/api/v1/admin/services", json=req_body)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_super_admin_on_create_service(admin_client, mock_conn):
    # Note: admin_client is actually super_admin from conftest.py
    req_body = {
        "name": "Test Service",
        "price_paise": 1000
    }
    mock_conn.fetchrow.return_value = {
        "id": str(uuid4()),
        "name": "Test Service",
        "name_tamil": None,
        "category": "General",
        "description": "Test",
        "description_tamil": None,
        "price_paise": 1000,
        "is_active": True,
        "max_persons": 5,
        "advance_booking_days": 1,
        "session": "na",
        "image_url": None,
        "sort_order": 0,
        "created_at": "2026-10-10T00:00:00Z",
        "updated_at": "2026-10-10T00:00:00Z"
    }
    response = admin_client.post("/api/v1/admin/services", json=req_body)
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_admin_on_update_role(standard_admin_client):
    response = standard_admin_client.patch(f"/api/v1/admin/users/{uuid4()}/role", json={"role": "admin"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_super_admin_on_update_role(admin_client, mock_conn):
    user_id = str(uuid4())
    mock_conn.fetchrow.return_value = {
        "id": user_id,
        "role": "devotee"
    }
    response = admin_client.patch(f"/api/v1/admin/users/{user_id}/role", json={"role": "admin"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_no_token_on_admin(client):
    response = client.get("/api/v1/admin/bookings")
    assert response.status_code == 403
