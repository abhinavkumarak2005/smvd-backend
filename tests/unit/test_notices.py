import pytest
from datetime import datetime, timedelta, timezone

def get_base_notice():
    return {
        "title": "Draft",
        "title_tamil": "Draft Tamil",
        "body": "Body",
        "body_tamil": "Body Tamil",
        "category": "Alert",
        "priority": 10,
        "published_at": str(datetime.now(timezone.utc)),
        "expires_at": str(datetime.now(timezone.utc)),
        "created_at": str(datetime.now(timezone.utc))
    }

@pytest.mark.asyncio
async def test_create_draft_notice(admin_client, mock_conn):
    req_body = {
        "title": "Test Notice",
        "body": "This is a test notice",
        "category": "Alert",
        "priority": 100,
        "status": "draft"
    }
    
    mock_conn.fetchrow.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        **get_base_notice(),
        **req_body
    }
    
    response = admin_client.post("/api/v1/admin/notices", json=req_body)
    assert response.status_code == 201
    
@pytest.mark.asyncio
async def test_public_notices_excludes_draft(client, mock_conn):
    mock_conn.fetch.return_value = [
        {
            "id": "11111111-1111-1111-1111-111111111111", 
            **get_base_notice(),
            "status": "active", 
            "title": "Active Notice",
        }
    ]
    
    response = client.get("/api/v1/notices")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "active"
    
@pytest.mark.asyncio
async def test_activate_notice(admin_client, mock_conn):
    mock_conn.fetchrow.side_effect = [
        {"id": "22222222-2222-2222-2222-222222222222", **get_base_notice(), "status": "draft"},
        {"id": "22222222-2222-2222-2222-222222222222", **get_base_notice(), "status": "active"}
    ]
    
    response = admin_client.patch("/api/v1/admin/notices/22222222-2222-2222-2222-222222222222/activate")
    assert response.status_code == 200
    assert response.json()["message"] == "Notice activated"
    
@pytest.mark.asyncio
async def test_schedule_future_notice(admin_client, mock_conn):
    future_date = datetime.now(timezone.utc) + timedelta(days=5)
    
    req_body = {
        "title": "Future Notice",
        "body": "This is a future notice",
        "category": "Info",
        "priority": 50,
        "status": "scheduled",
        "published_at": future_date.isoformat()
    }
    
    mock_conn.fetchrow.return_value = {
        "id": "22222222-2222-2222-2222-222222222222",
        **get_base_notice(),
        **req_body
    }
    
    response = admin_client.post("/api/v1/admin/notices", json=req_body)
    assert response.status_code == 201
    assert response.json()["status"] == "scheduled"
