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
MOOLAVAR_SERVICE_ID = uuid4()

def get_moolavar_request(num_persons=3):
    return BookingCreateRequest(
        service_id=MOOLAVAR_SERVICE_ID,
        booking_date=datetime.now(timezone.utc).date() + timedelta(days=5),
        session="morning",
        num_persons=num_persons,
        persons=[PersonRequest(full_name=f"Devotee {i}", star="Ashwini") for i in range(num_persons)]
    )

@pytest.fixture
def mock_moolavar_deps():
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
        mock_srv.return_value = {"id": MOOLAVAR_SERVICE_ID, "is_active": True, "advance_booking_days": 1, "default_capacity": 10, "name": "Moolavar Abishegam", "price_paise": 100000}
        mock_conf.return_value = ConflictResult(blocked=False, requires_approval=False)
        mock_dup.return_value = False
        
        mock_slot_create.return_value = {"id": uuid4()}
        # By default, slot is empty
        mock_slot_update.return_value = {"id": uuid4(), "is_blocked": False, "total_capacity": 10, "confirmed_count": 0, "pending_count": 0}
        
        mock_create_bkg.return_value = {"id": uuid4()}
        mock_pay_order.return_value = {"id": "order_123"}
        
        yield {
            "update": mock_slot_update
        }

@pytest.mark.asyncio
async def test_moolavar_valid_persons(mock_moolavar_deps, mock_conn):
    # 3 persons is valid
    req = get_moolavar_request(3)
    res = await booking_engine.create_booking(mock_conn, USER_ID, req)
    
    assert res.booking_id is not None

@pytest.mark.asyncio
async def test_moolavar_invalid_persons(mock_moolavar_deps, mock_conn):
    # 4 persons should fail
    req = get_moolavar_request(4)
    
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
        
    assert exc.value.status_code == 422
    assert "Moolavar Abishegam allows maximum 3 persons" in exc.value.detail

@pytest.mark.asyncio
async def test_moolavar_11th_family_fails(mock_moolavar_deps, mock_conn):
    # Simulate slot is already booked for 10 families (capacity=10, confirmed=10)
    mock_moolavar_deps["update"].return_value = {"id": uuid4(), "is_blocked": False, "total_capacity": 10, "confirmed_count": 10, "pending_count": 0}
    
    req = get_moolavar_request(1)
    
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
        
    assert exc.value.status_code == 409
    assert "SLOT_FULL" in exc.value.detail
