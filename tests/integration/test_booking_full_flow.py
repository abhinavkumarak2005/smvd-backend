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
async def test_booking_full_flow(auth_client, fake_db, mock_conn):
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
        "pending_count": 0,
        "block_reason": None
    }
    
    async def mock_get_service(srv_id):
        return service if str(srv_id) == srv_id_str else None
        
    async def mock_get_or_create_slot(conn, s_id, d, sess, cap):
        return fake_db["slots"][slot_id]
        
    async def mock_get_slot_for_update(conn, s_id, d, sess):
        return fake_db["slots"][slot_id]
        
    async def mock_increment_pending(conn, s_id):
        fake_db["slots"][slot_id]["pending_count"] += 1
        
    async def mock_check_duplicate(*args):
        return False
        
    async def mock_create_booking(conn, data):
        data["id"] = booking_id
        fake_db["bookings"][booking_id] = data
        return data
        
    async def mock_create_order(amount, receipt):
        return {"id": order_id, "amount": amount, "currency": "INR"}
        
    async def mock_create_payment_record(conn, b_id, o_id, amt):
        fake_db["payments"][pay_id] = {
            "id": pay_id,
            "booking_id": b_id,
            "gateway_order_id": o_id,
            "amount_paise": amt,
            "status": "initiated"
        }
        
    async def mock_write_log(action, *args, **kwargs):
        fake_db["audit_logs"].append(action)

    with patch("app.services.booking_engine.service_repo.ServiceRepo.get_service", side_effect=mock_get_service), \
         patch("app.services.booking_engine.calendar_service.check_date") as mock_cal, \
         patch("app.services.booking_engine.conflict_checker.check_conflicts") as mock_conf, \
         patch("app.services.booking_engine.slot_inventory_repo.get_or_create_slot", side_effect=mock_get_or_create_slot), \
         patch("app.services.booking_engine.slot_inventory_repo.get_slot_for_update", side_effect=mock_get_slot_for_update), \
         patch("app.services.booking_engine.slot_inventory_repo.increment_pending", side_effect=mock_increment_pending), \
         patch("app.services.booking_engine.booking_repo.check_duplicate", side_effect=mock_check_duplicate), \
         patch("app.services.booking_engine.booking_repo.create_booking", side_effect=mock_create_booking), \
         patch("app.services.booking_engine.booking_repo.insert_persons", new_callable=AsyncMock), \
         patch("app.services.booking_engine.payment_service.create_order", side_effect=mock_create_order), \
         patch("app.services.booking_engine.payment_repo.create_payment_record", side_effect=mock_create_payment_record), \
         patch("app.routers.bookings.router.audit_service.write_log", side_effect=mock_write_log):
         
        # Mock responses
        from app.services.calendar_service import DateStatus
        from app.services.conflict_checker import ConflictResult
        mock_cal.return_value = DateStatus(status="open")
        mock_conf.return_value = ConflictResult(blocked=False, requires_approval=False)

        # 1. Create booking
        req = {
            "service_id": srv_id_str,
            "booking_date": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d"),
            "session": "morning",
            "num_persons": 2,
            "persons": [
                {"full_name": "Devotee One", "star": "Ashwini"},
                {"full_name": "Devotee Two", "star": "Bharani"}
            ]
        }
        
        res1 = auth_client.post("/api/v1/bookings", json=req)
        assert res1.status_code == 201
        
        resp_data = res1.json()
        assert resp_data["gateway_order_id"] == order_id
        assert fake_db["bookings"][booking_id]["status"] == "pending_payment"
        assert fake_db["slots"][slot_id]["pending_count"] == 1
        
        # Verify BackgroundTasks logic (in tests it might run synchronously if we are lucky, but TestClient doesn't await BackgroundTasks unless we use testclient properly). 
        # Actually starlette TestClient executes background tasks after sending response!
        assert "booking.created" in fake_db["audit_logs"]

    # 2. Simulate Webhook
    async def mock_webhook_fetchrow(query, *args):
        if "FROM payments" in query:
            return fake_db["payments"].get(pay_id)
        if "FROM bookings" in query:
            return fake_db["bookings"].get(booking_id)
        if "FROM slot_inventory" in query:
            return fake_db["slots"].get(slot_id)
        return None
        
    async def mock_webhook_execute(query, *args):
        if "UPDATE bookings SET status = $1" in query:
            fake_db["bookings"][booking_id]["status"] = args[0]
        elif "UPDATE payments SET status = 'success'" in query:
            fake_db["payments"][pay_id]["status"] = "success"
            
    async def mock_confirm_slot(conn, s_id):
        fake_db["slots"][slot_id]["pending_count"] -= 1
        fake_db["slots"][slot_id]["confirmed_count"] += 1

    with patch("app.routers.payments.webhook.webhook_service.verify_signature", return_value=True), \
         patch("app.services.webhook_service.slot_inventory_repo.confirm_slot", side_effect=mock_confirm_slot), \
         patch("app.services.webhook_service.audit_service.write_log", side_effect=mock_write_log), \
         patch("app.services.webhook_service.notification_service.send_sms", new_callable=AsyncMock), \
         patch("app.services.webhook_service.receipt_service.generate_receipt_pdf", new_callable=AsyncMock):
         
        mock_conn.fetchrow.side_effect = mock_webhook_fetchrow
        mock_conn.execute.side_effect = mock_webhook_execute

        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_123",
                        "order_id": order_id,
                        "amount": 50000
                    }
                }
            }
        }
        
        res2 = auth_client.post(
            "/api/v1/payments/webhook", 
            json=webhook_payload,
            headers={"X-Razorpay-Signature": "valid"}
        )
        assert res2.status_code == 200
        
        # Verify state
        assert fake_db["bookings"][booking_id]["status"] == "confirmed"
        assert fake_db["slots"][slot_id]["confirmed_count"] == 1
        assert fake_db["slots"][slot_id]["pending_count"] == 0
        assert "payment.success" in fake_db["audit_logs"]
