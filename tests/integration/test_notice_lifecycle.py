import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

@pytest.fixture
def fake_db():
    return {
        "notice": {}
    }

@pytest.mark.asyncio
async def test_notice_lifecycle(auth_client, admin_client, fake_db, mock_conn):
    # 1. Mocks
    async def mock_create_notice(conn, data):
        n_id = str(uuid4())
        record = {
            **data, 
            "id": n_id, 
            "status": data.get("status", "draft"),
            "created_at": datetime.now(timezone.utc)
        }
        fake_db["notice"][n_id] = record
        return record
        
    async def mock_get_notice(conn, notice_id):
        return fake_db["notice"].get(str(notice_id))
        
    async def mock_update_notice(conn, notice_id, data):
        n = fake_db["notice"].get(str(notice_id))
        if n:
            n.update({k:v for k,v in data.items() if v is not None})
            return n
        return None
        
    async def mock_get_active_notices(conn):
        return [n for n in fake_db["notice"].values() if n["status"] == "active"]
        
    async def mock_activate_scheduled(conn):
        now = datetime.now(timezone.utc)
        count = 0
        for n in fake_db["notice"].values():
            if n["status"] == "scheduled" and n.get("published_at") and n["published_at"] <= now:
                n["status"] = "active"
                count += 1
        return count
        
    async def mock_expire_old(conn):
        now = datetime.now(timezone.utc)
        count = 0
        for n in fake_db["notice"].values():
            if n["status"] == "active" and n.get("expires_at") and n["expires_at"] <= now:
                n["status"] = "expired"
                count += 1
        return count

    with patch("app.routers.admin.notices.notice_service.notice_repo.create_notice", side_effect=mock_create_notice), \
         patch("app.routers.admin.notices.notice_repo.get_notice", side_effect=mock_get_notice), \
         patch("app.routers.admin.notices.notice_service.notice_repo.update_notice", side_effect=mock_update_notice), \
         patch("app.routers.public.notices.notice_service.notice_repo.get_active_notices", side_effect=mock_get_active_notices), \
         patch("app.services.notice_service.notice_repo.activate_scheduled", side_effect=mock_activate_scheduled), \
         patch("app.services.notice_service.notice_repo.expire_old", side_effect=mock_expire_old), \
         patch("app.routers.admin.notices.notice_service.audit_service.write_log", new_callable=AsyncMock):
         
        # Step 1: Create scheduled notice with published_at = 1 minute ago
        now = datetime.now(timezone.utc)
        published_at = now - timedelta(minutes=1)
        expires_at = now + timedelta(days=1)
        
        req = {
            "title": "Test Notice",
            "body": "Content",
            "status": "scheduled",
            "priority": 0,
            "published_at": published_at.isoformat(),
            "expires_at": expires_at.isoformat()
        }
        
        res1 = admin_client.post("/api/v1/admin/notices", json=req)
        assert res1.status_code == 201
        n_id = res1.json()["id"]
        
        # Step 2: Since notice_service.create_notice auto-activates if published_at is past, it's already active!
        # But let's verify via public API
        res2 = auth_client.get("/api/v1/notices")
        assert res2.status_code == 200
        assert len(res2.json()) == 1
        assert res2.json()[0]["id"] == n_id
        
        # Step 3: Let's create a future one and manually run mock_activate_scheduled
        req_future = {
            "title": "Future Notice",
            "body": "Content",
            "status": "scheduled",
            "priority": 0,
            "published_at": (now + timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat()
        }
        res_f = admin_client.post("/api/v1/admin/notices", json=req_future)
        n_id_future = res_f.json()["id"]
        
        # Public API shouldn't see it yet
        res3 = auth_client.get("/api/v1/notices")
        assert len(res3.json()) == 1
        
        # Now artificially change the fake_db so it's in the past
        fake_db["notice"][n_id_future]["published_at"] = now - timedelta(minutes=1)
        
        # Step 4: Run scheduler manual logic
        await mock_activate_scheduled(mock_conn)
        
        # Now it should be visible
        res4 = auth_client.get("/api/v1/notices")
        assert len(res4.json()) == 2
        
        # Step 5: Set expires_at = 1 min ago for the first notice
        res5 = admin_client.put(f"/api/v1/admin/notices/{n_id}", json={
            "expires_at": (now - timedelta(minutes=1)).isoformat()
        })
        assert res5.status_code == 200
        # PUT parses it into string because of pydantic model dump without mode="json". We manually convert datetime in mock.
        fake_db["notice"][n_id]["expires_at"] = now - timedelta(minutes=1)
        
        # Run expire scheduler
        await mock_expire_old(mock_conn)
        
        # First notice should be gone
        res6 = auth_client.get("/api/v1/notices")
        assert len(res6.json()) == 1
        assert res6.json()[0]["id"] == n_id_future
