import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.models.schemas.booking import BookingCreateRequest, PersonRequest
from app.services import booking_engine
from app.services.conflict_checker import ConflictResult
from app.services.calendar_service import DateStatus

USER_ID = uuid4()
CHARIOT_SERVICE_ID = uuid4()

def get_chariot_request(session="morning"):
    return BookingCreateRequest(
        service_id=CHARIOT_SERVICE_ID,
        booking_date=datetime.now(timezone.utc).date() + timedelta(days=5),
        session=session,
        num_persons=1,
        persons=[PersonRequest(full_name="Devotee 1", star="Ashwini")]
    )

@pytest.fixture
def mock_chariot_deps():
    with patch("app.services.calendar_service.check_date") as mock_cal, \
         patch("app.repositories.service_repo.ServiceRepo.get_service") as mock_srv, \
         patch("app.services.conflict_checker.check_conflicts") as mock_conf, \
         patch("app.repositories.slot_inventory_repo.get_or_create_slot") as mock_slot_create, \
         patch("app.repositories.slot_inventory_repo.get_slot_for_update") as mock_slot_update, \
         patch("app.repositories.slot_inventory_repo.increment_pending") as mock_slot_inc, \
         patch("app.repositories.booking_repo.check_duplicate") as mock_dup, \
         patch("app.repositories.booking_repo.create_booking") as mock_create_bkg, \
         patch("app.repositories.booking_repo.insert_persons") as mock_ins_persons, \
         patch("app.services.payment_service.create_order") as mock_pay_order, \
         patch("app.repositories.payment_repo.create_payment_record") as mock_pay_rec:
         
        mock_cal.return_value = DateStatus(status="open")
        mock_srv.return_value = {"id": CHARIOT_SERVICE_ID, "is_active": True, "advance_booking_days": 1, "default_capacity": 1, "name": "Gold Chariot", "price_paise": 100000}
        mock_conf.return_value = ConflictResult(blocked=False, requires_approval=False)
        mock_dup.return_value = False
        
        mock_slot_create.return_value = {"id": uuid4()}
        # By default, slot is empty
        mock_slot_update.return_value = {"id": uuid4(), "is_blocked": False, "total_capacity": 1, "confirmed_count": 0, "pending_count": 0}
        
        mock_create_bkg.return_value = {"id": uuid4()}
        mock_pay_order.return_value = {"id": "order_123"}
        
        yield {
            "update": mock_slot_update
        }

@pytest.mark.asyncio
async def test_chariot_booking_success(mock_chariot_deps, mock_conn):
    req = get_chariot_request("morning")
    res = await booking_engine.create_booking(mock_conn, USER_ID, req)
    
    assert res.booking_id is not None
    assert res.gateway_order_id == "order_123"

@pytest.mark.asyncio
async def test_chariot_booking_slot_full(mock_chariot_deps, mock_conn):
    # Simulate slot is already booked (capacity=1, confirmed=1)
    mock_chariot_deps["update"].return_value = {"id": uuid4(), "is_blocked": False, "total_capacity": 1, "confirmed_count": 1, "pending_count": 0}
    
    req = get_chariot_request("morning")
    
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
        
    assert exc.value.status_code == 409
    assert "SLOT_FULL" in exc.value.detail

@pytest.mark.asyncio
async def test_chariot_morning_and_evening_success(mock_chariot_deps, mock_conn):
    # Both morning and evening should succeed individually since they are different sessions
    req_morn = get_chariot_request("morning")
    res_morn = await booking_engine.create_booking(mock_conn, USER_ID, req_morn)
    assert res_morn.booking_id is not None
    
    req_eve = get_chariot_request("evening")
    res_eve = await booking_engine.create_booking(mock_conn, USER_ID, req_eve)
    assert res_eve.booking_id is not None
