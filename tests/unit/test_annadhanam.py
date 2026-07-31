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
ANNADHANAM_SERVICE_ID = uuid4()

def get_annadhanam_request(num_persons=1):
    return BookingCreateRequest(
        service_id=ANNADHANAM_SERVICE_ID,
        booking_date=datetime.now(timezone.utc).date() + timedelta(days=5),
        session="morning",
        num_persons=num_persons,
        persons=[PersonRequest(full_name=f"Devotee {i}", star="Ashwini") for i in range(num_persons)]
    )

@pytest.fixture
def mock_annadhanam_deps():
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
        mock_srv.return_value = {"id": ANNADHANAM_SERVICE_ID, "is_active": True, "advance_booking_days": 1, "default_capacity": 100, "name": "Annadhanam", "price_paise": 50000}
        mock_conf.return_value = ConflictResult(blocked=False, requires_approval=False)
        mock_dup.return_value = False
        
        mock_slot_create.return_value = {"id": uuid4()}
        # By default, slot is empty
        mock_slot_update.return_value = {"id": uuid4(), "is_blocked": False, "total_capacity": 100, "confirmed_count": 0, "pending_count": 0}
        
        mock_create_bkg.return_value = {"id": uuid4()}
        mock_pay_order.return_value = {"id": "order_123"}
        
        yield {
            "update": mock_slot_update
        }

@pytest.mark.asyncio
async def test_annadhanam_valid_persons(mock_annadhanam_deps, mock_conn):
    # 1 person is valid
    req = get_annadhanam_request(1)
    res = await booking_engine.create_booking(mock_conn, USER_ID, req)
    
    assert res.booking_id is not None

@pytest.mark.asyncio
async def test_annadhanam_invalid_persons(mock_annadhanam_deps, mock_conn):
    # 2 persons should fail
    req = get_annadhanam_request(2)
    
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
        
    assert exc.value.status_code == 422
    assert "Annadhanam bookings require exactly 1 primary person" in exc.value.detail
