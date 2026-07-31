import pytest
import uuid
from unittest.mock import patch

@pytest.mark.asyncio
async def test_preference_local_delivery(client, mock_conn):
    transaction_id = str(uuid.uuid4())
    
    mock_conn.fetchrow.side_effect = [
        {"id": transaction_id, "amount_paise": 10000, "status": "success", "certificate_status": "pending_details", "donor_phone": "123", "donor_email": "test@test.com"}, # Get transaction
        {"id": transaction_id} # update transaction
    ]
    
    req_body = {
        "delivery_mode": "in_person",
        "donor_location_type": "local"
    }
    
    response = client.post(f"/api/v1/e-undiyal/{transaction_id}/certificate-preference", json=req_body)
    assert response.status_code == 200
    assert response.json()["message"] == "Preference submitted. Your certificate will be ready for collection at the temple office."

@pytest.mark.asyncio
async def test_preference_duplicate_submission(client, mock_conn):
    transaction_id = str(uuid.uuid4())
    
    mock_conn.fetchrow.return_value = {
        "id": transaction_id,
        "amount_paise": 10000,
        "status": "success",
        "certificate_status": "ready",
        "donor_phone": "123",
        "donor_email": "test@test.com"
    }
    
    req_body = {
        "delivery_mode": "in_person",
        "donor_location_type": "local"
    }
    
    response = client.post(f"/api/v1/e-undiyal/{transaction_id}/certificate-preference", json=req_body)
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_domestic_delivery_missing_pan(client, mock_conn):
    transaction_id = str(uuid.uuid4())
    mock_conn.fetchrow.return_value = {
        "id": transaction_id,
        "amount_paise": 10000,
        "status": "success",
        "certificate_status": "pending_details",
        "donor_phone": "123",
        "donor_email": "test@test.com"
    }
    
    req_body = {
        "delivery_mode": "courier",
        "donor_location_type": "domestic",
        "donor_address": {
            "full_name": "Test",
            "door_no": "1",
            "street": "Test St",
            "city": "City",
            "state": "State",
            "pincode": "123456",
            "country": "India",
            "phone": "9876543210"
        }
    }
    
    response = client.post(f"/api/v1/e-undiyal/{transaction_id}/certificate-preference", json=req_body)
    assert response.status_code == 422
    assert "pan" in response.text.lower()

@pytest.mark.asyncio
async def test_domestic_delivery_invalid_pan(client, mock_conn):
    transaction_id = str(uuid.uuid4())
    mock_conn.fetchrow.return_value = {
        "id": transaction_id,
        "amount_paise": 10000,
        "status": "success",
        "certificate_status": "pending_details",
        "donor_phone": "123",
        "donor_email": "test@test.com"
    }
    
    req_body = {
        "delivery_mode": "courier",
        "donor_location_type": "domestic",
        "donor_address": {
            "full_name": "Test",
            "door_no": "1",
            "street": "Test St",
            "city": "City",
            "state": "State",
            "pincode": "123456",
            "country": "India",
            "phone": "9876543210",
            "pan_number": "INVALID123"
        }
    }
    
    response = client.post(f"/api/v1/e-undiyal/{transaction_id}/certificate-preference", json=req_body)
    assert response.status_code == 422
    assert "pan" in response.text.lower()

@pytest.mark.asyncio
@patch("app.services.certificate_service.notification_service.send_sms")
async def test_admin_issues_certificate(mock_send_sms, admin_client, mock_conn):
    transaction_id = str(uuid.uuid4())
    
    mock_conn.fetchval.return_value = 0
    mock_conn.fetchrow.side_effect = [
        {"id": transaction_id, "amount_paise": 10000, "status": "success", "certificate_status": "pending_issue", "donor_phone": "+919999999999", "donor_email": "test@test.com"},
        {"id": transaction_id, "certificate_status": "ready"}
    ]
    
    req_body = {
        "certificate_url": "https://example.com/cert.pdf",
        "receipt_url": "https://example.com/receipt.pdf"
    }
    
    response = admin_client.post(f"/api/v1/admin/certificates/{transaction_id}/issue", json=req_body)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Certificate issued"
    mock_send_sms.assert_called_once()
