import pytest
from unittest.mock import patch, AsyncMock
from httpx import Response
import httpx
from datetime import datetime, timedelta, timezone
from jose import jwt

from app.config import get_settings

settings = get_settings()

@pytest.fixture
def mock_supabase_verify():
    with patch("httpx.AsyncClient.post") as mock_post:
        yield mock_post

@pytest.mark.asyncio
async def test_verify_otp_success(client, mock_conn, mock_supabase_verify):
    # Mock supabase response
    mock_supabase_verify.return_value = Response(
        200, 
        json={
            "access_token": "valid_access_token",
            "refresh_token": "valid_refresh_token",
            "user": {
                "id": "11111111-1111-1111-1111-111111111111",
                "phone": "+919876543210"
            }
        }
    )
    
    # Mock db fetchrow for users table upsert
    mock_conn.fetchrow.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "phone": "+919876543210",
        "email": None,
        "role": "devotee",
        "created_at": datetime.now(timezone.utc)
    }

    req_body = {
        "phone": "+919876543210",
        "otp": "123456"
    }

    response = client.post("/api/v1/auth/otp/verify", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["profile"]["role"] == "devotee"

@pytest.mark.asyncio
async def test_verify_otp_invalid(client, mock_supabase_verify):
    mock_supabase_verify.return_value = Response(400, json={"msg": "Token has expired or is invalid"})

    req_body = {
        "phone": "+919876543210",
        "otp": "000000"
    }

    response = client.post("/api/v1/auth/otp/verify", json=req_body)
    assert response.status_code == 401
    assert "Invalid OTP" in response.text

@pytest.mark.asyncio
async def test_otp_rate_limit_exceeded(client, mock_supabase_verify):
    mock_supabase_verify.return_value = Response(429, json={"msg": "Too many requests"})
    
    req_body = {
        "phone": "+919876543210"
    }
    
    response = client.post("/api/v1/auth/otp/send", json=req_body)
    assert response.status_code == 429
    assert "Too many requests" in response.text

@pytest.mark.asyncio
async def test_unauthenticated_client_forbidden(client):
    # Call an endpoint that requires auth (e.g. /api/v1/e-undiyal which requires devotee role)
    response = client.get("/api/v1/e-undiyal")
    # Because client doesn't provide Authorization header, should return 401/403
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_devotee_on_admin_route(auth_client):
    # Attempt to access an admin route with devotee token
    response = auth_client.get("/api/v1/admin/services")
    # Because auth_client has 'devotee' role, it should be Forbidden (403)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_admin_on_admin_route(admin_client, mock_conn):
    mock_conn.fetch.return_value = []
    # Admin trying to access admin route
    response = admin_client.get("/api/v1/admin/services")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_expired_jwt(client):
    # Create an expired token manually
    expired_payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "role": "devotee",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5)
    }
    expired_token = jwt.encode(expired_payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    
    response = client.get(
        "/api/v1/e-undiyal", 
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
