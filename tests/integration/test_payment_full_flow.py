import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta, timezone

@pytest.fixture
def fake_db():
    return {
        "bookings": {},
        "payments": {},
        "slots": {},
        "services": {
            "srv_1": {
                "id": uuid4(),
                "name": "General Darshan",
                "is_active": True,
                "advance_booking_days": 1,
                "default_capacity": 100,
                "price_paise": 50000
            }
        },
        "audit_logs": []
    }

@pytest.mark.asyncio
async def test_payment_full_flow(auth_client, fake_db, mock_conn):
    user_id = "11111111-1111-1111-1111-111111111111"
    service = fake_db["services"]["srv_1"]
    srv_id_str = str(service["id"])
    booking_id = str(uuid4())
    slot_id = str(uuid4())
    pay_id = str(uuid4())
    order_id = "order_123"
    
    # Pre-seed slot
    fake_db["slots"][slot_id] = {
        "id": slot_id,
        "service_id": srv_id_str,
        "is_blocked": False,
        "total_capacity": 100,
        "confirmed_count": 0,
        "pending_count": 1,
        "block_reason": None
    }
    
    # Pre-seed booking in pending_payment
    fake_db["bookings"][booking_id] = {
        "id": booking_id,
        "service_id": srv_id_str,
        "slot_id": slot_id,
        "status": "pending_payment",
        "requires_approval": False
    }
    
    fake_db["payments"][pay_id] = {
        "id": pay_id,
        "booking_id": booking_id,
        "gateway_order_id": order_id,
        "amount_paise": 50000,
        "status": "initiated"
    }

    # 1. Simulate Payment Failed Webhook
    async def mock_webhook_fetchrow(query, *args):
        if "FROM payments" in query:
            return fake_db["payments"].get(pay_id)
        if "FROM bookings" in query:
            return fake_db["bookings"].get(booking_id)
        if "FROM slot_inventory" in query:
            return fake_db["slots"].get(slot_id)
        return None
        
    async def mock_webhook_execute(query, *args):
        if "UPDATE bookings SET status = 'payment_failed'" in query:
            fake_db["bookings"][booking_id]["status"] = "payment_failed"
        elif "UPDATE payments SET status = 'failed'" in query:
            fake_db["payments"][pay_id]["status"] = "failed"
            
    async def mock_decrement_pending(conn, s_id):
        fake_db["slots"][slot_id]["pending_count"] -= 1

    with patch("app.routers.payments.webhook.webhook_service.verify_signature", return_value=True), \
         patch("app.services.webhook_service.slot_inventory_repo.decrement_pending", side_effect=mock_decrement_pending), \
         patch("app.services.webhook_service.audit_service.write_log", new_callable=AsyncMock), \
         patch("app.services.webhook_service.notification_service.send_sms", new_callable=AsyncMock):
         
        mock_conn.fetchrow.side_effect = mock_webhook_fetchrow
        mock_conn.execute.side_effect = mock_webhook_execute

        webhook_payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_123",
                        "order_id": order_id
                    }
                }
            }
        }
        
        res = auth_client.post(
            "/api/v1/payments/webhook", 
            json=webhook_payload,
            headers={"X-Razorpay-Signature": "valid"}
        )
        assert res.status_code == 200
        
        # Verify state: Booking should be failed, slot released
        assert fake_db["bookings"][booking_id]["status"] == "payment_failed"
        assert fake_db["slots"][slot_id]["pending_count"] == 0
        assert fake_db["slots"][slot_id]["confirmed_count"] == 0
