import pytest
import uuid

@pytest.mark.asyncio
async def test_public_services_only_active(client, mock_conn):
    base_service = {
        "name_tamil": "Tamil",
        "category": "Archana",
        "description": "Desc",
        "description_tamil": "Tamil Desc",
        "price_paise": 1000,
        "max_persons": 1,
        "advance_booking_days": 30,
        "session": "Morning",
        "image_url": "http://image",
        "sort_order": 1,
        "created_at": "2026-01-01"
    }
    
    mock_conn.fetch.return_value = [
        {"id": str(uuid.uuid4()), "name": "Active Service", "is_active": True, **base_service}
    ]
    
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Active Service"
    
@pytest.mark.asyncio
async def test_admin_services_includes_inactive(admin_client, mock_conn):
    base_service = {
        "name_tamil": "Tamil",
        "category": "Archana",
        "description": "Desc",
        "description_tamil": "Tamil Desc",
        "price_paise": 1000,
        "max_persons": 1,
        "advance_booking_days": 30,
        "session": "Morning",
        "image_url": "http://image",
        "sort_order": 1,
        "created_at": "2026-01-01"
    }
    
    mock_conn.fetch.return_value = [
        {"id": str(uuid.uuid4()), "name": "Active Service", "is_active": True, **base_service},
        {"id": str(uuid.uuid4()), "name": "Inactive Service", "is_active": False, **base_service}
    ]
    
    response = admin_client.get("/api/v1/admin/services")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
@pytest.mark.asyncio
async def test_super_admin_toggle_service(admin_client, mock_conn):
    service_id = str(uuid.uuid4())
    
    base_service = {
        "name_tamil": "Tamil",
        "category": "Archana",
        "description": "Desc",
        "description_tamil": "Tamil Desc",
        "price_paise": 1000,
        "max_persons": 1,
        "advance_booking_days": 30,
        "session": "Morning",
        "image_url": "http://image",
        "sort_order": 1,
        "created_at": "2026-01-01"
    }

    mock_conn.fetchrow.side_effect = [
        {"id": service_id, "name": "Test", "is_active": True, **base_service}, # get service
        {"id": service_id, "name": "Test", "is_active": False, **base_service} # update service
    ]
    
    req_body = {"is_active": False}
    
    # Needs super_admin role. Our admin_client mocks this role too.
    response = admin_client.patch(f"/api/v1/admin/services/{service_id}/toggle")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Service is now inactive"
