import pytest
import asyncio
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.models.schemas.booking import BookingCreateRequest, PersonRequest
from app.services import booking_engine
from app.services.calendar_service import DateStatus
from app.services.conflict_checker import ConflictResult

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
                "default_capacity": 5,
                "price_paise": 50000
            }
        }
    }

@pytest.mark.asyncio
async def test_capacity_concurrency(fake_db):
    service = fake_db["services"]["srv_1"]
    srv_id_str = str(service["id"])
    slot_id = str(uuid4())
    
    fake_db["slots"][slot_id] = {
        "id": slot_id,
        "service_id": srv_id_str,
        "is_blocked": False,
        "total_capacity": 5,
        "confirmed_count": 0,
        "pending_count": 0,
        "block_reason": None
    }
    
    # Simulate DB locks with asyncio.Lock
    slot_lock = asyncio.Lock()
    
    async def mock_get_service(srv_id):
        return service if str(srv_id) == srv_id_str else None
        
    async def mock_get_or_create_slot(conn, s_id, d, sess, cap):
        return fake_db["slots"][slot_id]
        
    async def mock_get_slot_for_update(conn, s_id, d, sess):
        # The lock simulates FOR UPDATE
        await slot_lock.acquire()
        # Return a copy to avoid reference sharing masking issues, but fake_db is truth
        return dict(fake_db["slots"][slot_id])
        
    async def mock_increment_pending(conn, s_id):
        fake_db["slots"][slot_id]["pending_count"] += 1
        slot_lock.release()
        
    async def mock_check_duplicate(*args):
        return False
        
    async def mock_create_booking(conn, data):
        b_id = str(uuid4())
        data["id"] = b_id
        fake_db["bookings"][b_id] = data
        return data
        
    async def mock_create_order(amount, receipt):
        return {"id": f"order_{uuid4()}", "amount": amount, "currency": "INR"}
        
    async def mock_create_payment_record(conn, b_id, o_id, amt):
        pass

    async def mock_check_date(*args):
        return DateStatus(status="open")
        
    async def mock_check_conflicts(*args):
        return ConflictResult(blocked=False, requires_approval=False)

    with patch("app.services.booking_engine.service_repo.ServiceRepo.get_service", side_effect=mock_get_service), \
         patch("app.services.booking_engine.calendar_service.check_date", side_effect=mock_check_date), \
         patch("app.services.booking_engine.conflict_checker.check_conflicts", side_effect=mock_check_conflicts), \
         patch("app.services.booking_engine.slot_inventory_repo.get_or_create_slot", side_effect=mock_get_or_create_slot), \
         patch("app.services.booking_engine.slot_inventory_repo.get_slot_for_update", side_effect=mock_get_slot_for_update), \
         patch("app.services.booking_engine.slot_inventory_repo.increment_pending", side_effect=mock_increment_pending), \
         patch("app.services.booking_engine.booking_repo.check_duplicate", side_effect=mock_check_duplicate), \
         patch("app.services.booking_engine.booking_repo.create_booking", side_effect=mock_create_booking), \
         patch("app.services.booking_engine.booking_repo.insert_persons", new_callable=AsyncMock), \
         patch("app.services.booking_engine.payment_service.create_order", side_effect=mock_create_order), \
         patch("app.services.booking_engine.payment_repo.create_payment_record", side_effect=mock_create_payment_record):
         
        # Simulate 20 concurrent requests directly against the engine
        req = BookingCreateRequest(
            service_id=service["id"],
            booking_date=datetime.now(timezone.utc).date() + timedelta(days=5),
            session="morning",
            num_persons=1,
            persons=[PersonRequest(full_name="User", star="Ashwini")]
        )
        
        class MockTransaction:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, *args):
                # Release the row lock when the transaction ends (commit or rollback)
                if slot_lock.locked():
                    slot_lock.release()
            
        async def make_request(i):
            from unittest.mock import MagicMock
            mock_conn = MagicMock()
            mock_conn.transaction.return_value = MockTransaction()
            try:
                res = await booking_engine.create_booking(mock_conn, uuid4(), req)
                return "SUCCESS"
            except HTTPException as e:
                if "SLOT_FULL" in e.detail:
                    # Release lock if it was acquired but we failed capacity
                    if slot_lock.locked():
                        slot_lock.release()
                    return "SLOT_FULL"
                return f"ERROR: {e.detail}"
            except Exception as e:
                import traceback
                with open("error.log", "a") as f:
                    f.write(f"FAIL: {str(e)} Type: {type(e)}\n{traceback.format_exc()}\n")
                if slot_lock.locked():
                    slot_lock.release()
                return "FAIL"

        tasks = [make_request(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        success_count = results.count("SUCCESS")
        full_count = results.count("SLOT_FULL")
        
        # Verify exactly 5 succeeded
        assert success_count == 5, f"Expected 5 SUCCESS, got {success_count}. Results: {results}"
        assert full_count == 15, f"Expected 15 SLOT_FULL, got {full_count}. Results: {results}"
        
        # Verify exactly 5 pending slots
        assert fake_db["slots"][slot_id]["pending_count"] == 5
        assert fake_db["slots"][slot_id]["confirmed_count"] == 0
