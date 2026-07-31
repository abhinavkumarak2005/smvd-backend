import pytest
from unittest.mock import patch

@pytest.mark.asyncio
@patch("app.services.e_undiyal_service.payment_service.create_order")
async def test_initiate_donation_success(mock_create_order, client, mock_conn):
    # Setup mocks
    mock_create_order.return_value = {"id": "order_123"}
    mock_conn.fetchval.return_value = 0
    
    mock_conn.fetchrow.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "transaction_reference": "ref_123",
        "razorpay_order_id": "order_123",
        "amount_paise": 50000
    }
    
    req_body = {
        "amount_paise": 50000,
        "donor_name": "Test User",
        "donor_phone": "+919999999999",
        "pan_number": "ABCDE1234F"
    }
    
    response = client.post("/api/v1/e-undiyal/initiate", json=req_body)
    
    # 201 Created is the expected response from the router
    assert response.status_code == 201
    data = response.json()
    assert data["gateway_order_id"] == "order_123"
    
@pytest.mark.asyncio
async def test_donation_minimum_amount_enforced(client, mock_conn):
    req_body = {
        "amount_paise": 50, # 50 paise is below 1 Rupee
        "donor_name": "Test User",
        "donor_phone": "+919999999999"
    }
    
    response = client.post("/api/v1/e-undiyal/initiate", json=req_body)
    assert response.status_code == 422
