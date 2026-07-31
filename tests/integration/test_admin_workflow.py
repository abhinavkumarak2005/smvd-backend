import pytest
from uuid import uuid4
from datetime import date
from unittest.mock import patch, AsyncMock

@pytest.fixture
def fake_db():
    srv_id = str(uuid4())
    slot_id = str(uuid4())
    
    return {
        "booking": {},
        "payment": {},
        "slot": {
            slot_id: {
                "id": slot_id,
                "total_capacity": 5,
                "confirmed_count": 0,
                "pending_count": 0,
                "is_blocked": False,
                "date": date(2026, 10, 10),
                "session": "morning"
            }
        },
        "service": {
            srv_id: {
                "id": srv_id,
                "name": "Special Darshan",
                "price_paise": 50000,
                "requires_approval": True,
                "default_capacity": 50,
                "is_active": True,
                "advance_booking_days": 1,
                "max_persons": 5
            }
        }
    }

@pytest.mark.asyncio
async def test_admin_approval_workflow(auth_client, admin_client, fake_db, mock_conn):
    booking_id = str(uuid4())
    pay_id = str(uuid4())
    user_id = "11111111-1111-1111-1111-111111111111"
    
    # 1. Mock DB Behaviors
    async def mock_get_service(service_id):
        return fake_db["service"].get(str(service_id))
        
    class DateStatus:
        def __init__(self):
            self.is_blocked = False
            self.is_holiday = False
            self.notes = None
            self.status = "available"
            
    async def mock_check_date(conn, target_date, service_id):
        return DateStatus()
        
    class ConflictStatus:
        def __init__(self):
            self.blocked = False
            self.message = None
            self.requires_approval = False
            self.notice = None

    async def mock_check_conflicts(conn, service_id, target_date, session):
        return ConflictStatus()
        
    async def mock_get_slot(*args, **kwargs):
        slot_id = list(fake_db["slot"].keys())[0]
        return fake_db["slot"][slot_id]
        
    async def mock_increment_pending(conn, slot_id, count=1):
        fake_db["slot"][slot_id]["pending_count"] += count
        
    async def mock_release_slot(conn, booking_id):
        b = fake_db["booking"][str(booking_id)]
        fake_db["slot"][b["slot_id"]]["pending_count"] -= b["num_persons"]
        
    async def mock_create_booking(conn, data):
        b_id = data.get("id", str(uuid4()))
        record = {**data, "id": b_id}
        fake_db["booking"][b_id] = record
        return record
        
    async def mock_insert_persons(*args):
        pass
        
    async def mock_create_payment_record(conn, booking_id, gateway_order_id, amount_paise):
        p_id = str(uuid4())
        record = {"id": p_id, "booking_id": str(booking_id), "amount_paise": amount_paise, "status": "pending"}
        fake_db["payment"][p_id] = record
        return record
        
    async def mock_get_booking(conn, b_id):
        b_id_str = str(b_id)
        b = fake_db["booking"].get(b_id_str)
        if b:
            # find payment
            p = next((pay for pay in fake_db["payment"].values() if pay["booking_id"] == b_id_str), None)
            return {**b, "payment": p}
        return None
        
    async def mock_update_status(conn, b_id, status, admin_id=None, note=None):
        fake_db["booking"][str(b_id)]["status"] = status
        
    # --- Mocks for the webhook ---
    async def mock_fetchrow(query, *args):
        if "payments WHERE gateway_order_id" in query:
            return next((p for p in fake_db["payment"].values() if p.get("gateway_order_id") == args[0]), None)
        if "bookings WHERE id" in query:
            return fake_db["booking"].get(args[0])
        if "slot_inventory WHERE id" in query:
            return fake_db["slot"].get(args[0])
        return None
        
    async def mock_execute(query, *args):
        if "UPDATE bookings SET status" in query:
            fake_db["booking"][args[1]]["status"] = args[0]
        if "UPDATE payments SET status = 'success'" in query:
            fake_db["payment"][args[1]]["status"] = "success"
            
    async def mock_confirm_slot(conn, slot_id):
        pass # Not needed for pending_approval flow

    # 2. Patch dependencies
    with patch("app.services.booking_engine.calendar_service.check_date", side_effect=mock_check_date), \
         patch("app.services.booking_engine.conflict_checker.check_conflicts", side_effect=mock_check_conflicts), \
         patch("app.services.booking_engine.slot_inventory_repo.get_or_create_slot", side_effect=mock_get_slot), \
         patch("app.services.booking_engine.slot_inventory_repo.get_slot_for_update", side_effect=mock_get_slot), \
         patch("app.services.booking_engine.slot_inventory_repo.increment_pending", side_effect=mock_increment_pending), \
         patch("app.services.booking_engine.booking_repo.create_booking", side_effect=mock_create_booking), \
         patch("app.services.booking_engine.booking_repo.insert_persons", side_effect=mock_insert_persons), \
         patch("app.services.booking_engine.booking_repo.check_duplicate", return_value=False), \
         patch("app.services.booking_engine.payment_repo.create_payment_record", side_effect=mock_create_payment_record), \
         patch("app.services.booking_engine.payment_service.create_order", return_value={"id": "order_123"}), \
         patch("app.routers.admin.bookings.booking_repo.get_booking", side_effect=mock_get_booking), \
         patch("app.routers.admin.bookings.booking_repo.update_status", side_effect=mock_update_status), \
         patch("app.routers.admin.bookings.slot_inventory_repo.release_slot", side_effect=mock_release_slot), \
         patch("app.routers.admin.bookings.notification_service.send_sms", new_callable=AsyncMock), \
         patch("app.routers.payments.webhook.webhook_service.verify_signature", return_value=True), \
         patch("app.services.booking_engine.service_repo.ServiceRepo.get_service", side_effect=mock_get_service):
         
        mock_conn.fetchrow.side_effect = mock_fetchrow
        mock_conn.execute.side_effect = mock_execute
         
        # Step 1: Create booking
        srv_id = list(fake_db["service"].keys())[0]
        
        req = {
            "service_id": srv_id,
            "booking_date": "2026-10-10",
            "session": "morning",
            "num_persons": 1,
            "persons": [{"full_name": "Test", "star": "Test"}]
        }
        res1 = auth_client.post("/api/v1/bookings", json=req)
        assert res1.status_code == 201
        data1 = res1.json()
        b_id_1 = data1["booking_id"]
        
        # Link gateway order ID for the webhook to find it
        p_id = next(k for k, v in fake_db["payment"].items() if v["booking_id"] == b_id_1)
        fake_db["payment"][p_id]["gateway_order_id"] = "order_123"
        fake_db["booking"][b_id_1]["requires_approval"] = True
        fake_db["booking"][b_id_1]["num_persons"] = 1
        
        # Step 2: Simulate Payment Webhook
        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "order_id": "order_123",
                        "id": "pay_xyz",
                        "amount": 50000
                    }
                }
            }
        }
        res2 = auth_client.post("/api/v1/payments/webhook", json=webhook_payload)
        assert res2.status_code == 200
        assert fake_db["booking"][b_id_1]["status"] == "pending_approval"
        
        # Step 3: Admin Approves
        res3 = admin_client.post(f"/api/v1/admin/bookings/{b_id_1}/approve", json={"note": "ok"})
        assert res3.status_code == 200
        assert fake_db["booking"][b_id_1]["status"] == "approved"
        
        # Step 4: Create another booking -> Reject -> verify slot released
        res4 = auth_client.post("/api/v1/bookings", json=req)
        assert res4.status_code == 201
        b_id_2 = res4.json()["booking_id"]
        fake_db["booking"][b_id_2]["num_persons"] = 1
        
        # Reject it
        fake_db["booking"][b_id_2]["status"] = "pending_approval"
        res5 = admin_client.post(f"/api/v1/admin/bookings/{b_id_2}/reject", json={"reason": "no space"})
        assert res5.status_code == 200
        assert fake_db["booking"][b_id_2]["status"] == "rejected"
        
        # Step 5: Verify slot pending count went back down
        # initial is 0. 1st booking adds 1. 2nd adds 1. Reject removes 1. So it should be 1.
        slot_id = list(fake_db["slot"].keys())[0]
        assert fake_db["slot"][slot_id]["pending_count"] == 1
