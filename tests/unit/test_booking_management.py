import pytest
from uuid import uuid4
from unittest.mock import patch

@pytest.mark.asyncio
@patch("app.routers.admin.bookings.notification_service.send_sms")
async def test_approve_booking(mock_send_sms, admin_client, mock_conn):
    booking_id = str(uuid4())
    mock_conn.fetchrow.side_effect = [
        {
            "id": booking_id,
            "status": "pending_approval",
            "phone": "+919999999999"
        },
        None # Payment
    ]
    mock_conn.fetch.return_value = [] # Persons
    
    response = admin_client.post(f"/api/v1/admin/bookings/{booking_id}/approve", json={"note": "Looks good"})
    assert response.status_code == 200
    assert response.json()["message"] == "Booking approved"
    
    mock_send_sms.assert_called_once()
    assert "approved" in mock_send_sms.call_args[0][1]

@pytest.mark.asyncio
async def test_approve_already_confirmed_booking(admin_client, mock_conn):
    booking_id = str(uuid4())
    mock_conn.fetchrow.side_effect = [
        {
            "id": booking_id,
            "status": "approved", # Already approved
            "phone": "+919999999999"
        },
        None
    ]
    mock_conn.fetch.return_value = []
    
    response = admin_client.post(f"/api/v1/admin/bookings/{booking_id}/approve", json={"note": "Trying again"})
    # Expecting 400 as per router code
    assert response.status_code == 400
    assert "not pending approval" in response.text

@pytest.mark.asyncio
@patch("app.routers.admin.bookings.slot_inventory_repo.release_slot")
@patch("app.routers.admin.bookings.notification_service.send_sms")
async def test_reject_booking(mock_send_sms, mock_release_slot, admin_client, mock_conn):
    booking_id = str(uuid4())
    mock_conn.fetchrow.side_effect = [
        {
            "id": booking_id,
            "status": "pending_approval",
            "phone": "+919999999999"
        },
        None
    ]
    mock_conn.fetch.return_value = []
    
    response = admin_client.post(f"/api/v1/admin/bookings/{booking_id}/reject", json={"reason": "Rules not followed"})
    assert response.status_code == 200
    assert response.json()["message"] == "Booking rejected"
    
    mock_release_slot.assert_called_once()
    mock_send_sms.assert_called_once()
    assert "rejected" in mock_send_sms.call_args[0][1]

@pytest.mark.asyncio
@patch("app.routers.admin.bookings.payment_service.initiate_refund")
@patch("app.routers.admin.bookings.slot_inventory_repo.release_slot")
@patch("app.routers.admin.bookings.notification_service.send_sms")
async def test_cancel_booking(mock_send_sms, mock_release_slot, mock_refund, admin_client, mock_conn):
    booking_id = str(uuid4())
    mock_conn.fetchrow.side_effect = [
        { # 1. Booking row
            "id": booking_id,
            "status": "approved",
            "phone": "+919999999999",
        },
        { # 2. Payment row
            "id": "pay_123",
            "status": "success",
            "amount_paise": 10000
        }
    ]
    mock_conn.fetch.return_value = [] # Persons
    
    response = admin_client.post(f"/api/v1/admin/bookings/{booking_id}/cancel", json={"reason": "User requested"})
    assert response.status_code == 200
    assert response.json()["message"] == "Booking cancelled"
    
    mock_release_slot.assert_called_once()
    mock_refund.assert_called_once_with("pay_123", 10000)
    mock_send_sms.assert_called_once()
    assert "cancelled" in mock_send_sms.call_args[0][1]

@pytest.mark.asyncio
@patch("app.routers.admin.bookings.booking_repo.get_all_bookings")
async def test_list_bookings_filters(mock_get_all, admin_client):
    mock_get_all.return_value = []
    
    response = admin_client.get("/api/v1/admin/bookings?status=approved&date=2026-10-10")
    assert response.status_code == 200
    
    # Verify the parameters were passed down to the repo correctly
    kwargs = mock_get_all.call_args[1]
    assert kwargs.get("status") == "approved"
    assert str(kwargs.get("booking_date")) == "2026-10-10"
