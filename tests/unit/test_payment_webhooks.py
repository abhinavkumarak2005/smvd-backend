import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import hmac
import hashlib
import json

from app.services.webhook_service import verify_signature, process_payment_captured, process_payment_failed

def test_verify_signature_valid():
    secret = "test_secret"
    payload = b'{"event":"payment.captured"}'
    
    expected_mac = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = secret
        assert verify_signature(payload, expected_mac) == True

def test_verify_signature_invalid():
    secret = "test_secret"
    payload = b'{"event":"payment.captured"}'
    
    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = secret
        assert verify_signature(payload, "invalid_sig") == False

@pytest.mark.asyncio
async def test_process_payment_captured_success(mock_conn):
    payment_id = uuid4()
    booking_id = uuid4()
    order_id = "order_123"
    
    # Setup fetchrow side effects
    async def mock_fetchrow(query, *args):
        if "FROM payments" in query:
            return {"id": payment_id, "booking_id": booking_id, "status": "initiated", "amount_paise": 10000}
        if "FROM bookings" in query:
            return {"id": booking_id, "status": "pending_payment", "requires_approval": False, "slot_id": uuid4()}
        if "FROM slot_inventory" in query:
            return {"id": uuid4(), "total_capacity": 10, "confirmed_count": 0, "pending_count": 1}
        return None
        
    mock_conn.fetchrow.side_effect = mock_fetchrow
    
    with patch("app.services.webhook_service.slot_inventory_repo.confirm_slot", new_callable=AsyncMock) as mock_confirm:
        await process_payment_captured(mock_conn, {"order_id": order_id, "id": "pay_123", "amount": 10000})
        
        # Verify bookings table updated to confirmed
        update_calls = mock_conn.execute.call_args_list
        assert any("SET status = $1" in c[0][0] and c[0][1] == "confirmed" for c in update_calls)
        assert mock_confirm.called

@pytest.mark.asyncio
async def test_process_payment_captured_idempotency(mock_conn):
    # Return a payment that is ALREADY success
    mock_conn.fetchrow.return_value = {"id": uuid4(), "booking_id": uuid4(), "status": "success", "amount_paise": 10000}
    
    await process_payment_captured(mock_conn, {"order_id": "order_123", "id": "pay_123", "amount": 10000})
    
    # Execute should not be called because it returns early
    mock_conn.execute.assert_not_called()

@pytest.mark.asyncio
async def test_process_payment_captured_wrong_amount(mock_conn):
    # DB has 10000, webhook says 5000
    async def mock_fetchrow(query, *args):
        if "FROM payments" in query:
            return {"id": uuid4(), "booking_id": uuid4(), "status": "initiated", "amount_paise": 10000}
        if "FROM bookings" in query:
            return {"id": uuid4(), "status": "pending_payment", "requires_approval": False, "slot_id": uuid4()}
        return None
    
    mock_conn.fetchrow.side_effect = mock_fetchrow
    
    await process_payment_captured(mock_conn, {"order_id": "order_123", "id": "pay_123", "amount": 5000})
    
    # Should exit without updating status to confirmed
    mock_conn.execute.assert_not_called()

@pytest.mark.asyncio
async def test_process_payment_failed(mock_conn):
    async def mock_fetchrow(query, *args):
        if "FROM payments" in query:
            return {"id": uuid4(), "booking_id": uuid4(), "status": "initiated"}
        if "FROM bookings" in query:
            return {"id": uuid4(), "status": "pending_payment", "slot_id": uuid4()}
        return None
        
    mock_conn.fetchrow.side_effect = mock_fetchrow
    
    with patch("app.services.webhook_service.slot_inventory_repo.decrement_pending", new_callable=AsyncMock) as mock_dec:
        await process_payment_failed(mock_conn, {"order_id": "order_123"})
        
        # Verify payment failed and slot released
        update_calls = mock_conn.execute.call_args_list
        assert any("SET status = 'failed'" in c[0][0] for c in update_calls)
        assert any("SET status = 'payment_failed'" in c[0][0] for c in update_calls)
        assert mock_dec.called
