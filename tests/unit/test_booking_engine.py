import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException

from app.models.schemas.booking import BookingCreateRequest, PersonRequest
from app.services import booking_engine

# Dummy UUIDs
USER_ID = uuid4()
SERVICE_ID = uuid4()
SLOT_ID = uuid4()
BOOKING_ID = uuid4()

def get_valid_request(days_ahead=5, num_persons=2, service_name="General"):
    return BookingCreateRequest(
        service_id=SERVICE_ID,
        booking_date=datetime.now(timezone.utc).date() + timedelta(days=days_ahead),
        session="morning",
        num_persons=num_persons,
        persons=[PersonRequest(full_name=f"Person {i}", star="Ashwini") for i in range(num_persons)]
    )

@pytest.fixture
def mock_deps():
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
         
        # Set up default happy path
        # 1. Calendar
        mock_cal_status = AsyncMock()
        mock_cal_status.status = "open"
        mock_cal.return_value = mock_cal_status
        
        # 2. Service
        mock_srv.return_value = {
            "id": SERVICE_ID,
            "name": "General Service",
            "is_active": True,
            "advance_booking_days": 1,
            "default_capacity": 50,
            "price_paise": 10000
        }
        
        # 3. Conflict
        mock_conf_res = AsyncMock()
        mock_conf_res.blocked = False
        mock_conf_res.requires_approval = False
        mock_conf_res.notice = None
        mock_conf.return_value = mock_conf_res
        
        # 4. Slots
        mock_slot_create.return_value = {"id": SLOT_ID}
        mock_slot_update.return_value = {
            "id": SLOT_ID,
            "is_blocked": False,
            "confirmed_count": 5,
            "pending_count": 0,
            "total_capacity": 50
        }
        
        # 5. Booking
        mock_dup.return_value = False
        mock_create_bkg.return_value = {"id": BOOKING_ID}
        
        # 6. Payment
        mock_pay_order.return_value = {"id": "order_123"}
        
        yield {
            "cal": mock_cal,
            "srv": mock_srv,
            "conf": mock_conf,
            "slot_create": mock_slot_create,
            "slot_update": mock_slot_update,
            "slot_inc": mock_slot_inc,
            "dup": mock_dup,
            "create_bkg": mock_create_bkg,
            "ins_persons": mock_ins_persons,
            "pay_order": mock_pay_order,
            "pay_rec": mock_pay_rec
        }

@pytest.mark.asyncio
async def test_booking_success(mock_deps, mock_conn):
    req = get_valid_request()
    res = await booking_engine.create_booking(mock_conn, USER_ID, req)
    
    assert res.booking_id == BOOKING_ID
    assert res.gateway_order_id == "order_123"
    assert res.requires_approval is False
    mock_deps["create_bkg"].assert_called_once()
    mock_deps["pay_order"].assert_called_once()

@pytest.mark.asyncio
async def test_booking_past_date(mock_deps, mock_conn):
    req = get_valid_request(days_ahead=-1)
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
    assert exc.value.status_code == 422
    assert "Cannot book in the past" in exc.value.detail

@pytest.mark.asyncio
async def test_booking_advance_days_violation(mock_deps, mock_conn):
    # Service requires 3 days advance, we book 1 day advance
    mock_deps["srv"].return_value["advance_booking_days"] = 3
    req = get_valid_request(days_ahead=1)
    
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
    assert exc.value.status_code == 422
    assert "Must book at least 3 days in advance" in exc.value.detail

@pytest.mark.asyncio
async def test_booking_date_blocked(mock_deps, mock_conn):
    mock_cal_status = AsyncMock()
    mock_cal_status.status = "blocked"
    mock_cal_status.notes = "Temple Maintenance"
    mock_deps["cal"].return_value = mock_cal_status
    
    req = get_valid_request()
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
    assert exc.value.status_code == 409
    assert "DATE_BLOCKED" in exc.value.detail

@pytest.mark.asyncio
async def test_booking_slot_full(mock_deps, mock_conn):
    # Capacity 50, Booked 50
    mock_deps["slot_update"].return_value["confirmed_count"] = 50
    
    req = get_valid_request()
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
    assert exc.value.status_code == 409
    assert "SLOT_FULL" in exc.value.detail

@pytest.mark.asyncio
async def test_booking_duplicate(mock_deps, mock_conn):
    mock_deps["dup"].return_value = True
    
    req = get_valid_request()
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
    assert exc.value.status_code == 409
    assert "DUPLICATE_BOOKING" in exc.value.detail

@pytest.mark.asyncio
async def test_moolavar_abishegam_family_limit(mock_deps, mock_conn):
    mock_deps["srv"].return_value["name"] = "Moolavar Abishegam"
    req = get_valid_request(num_persons=5) # Over 3 limit
    
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
    assert exc.value.status_code == 422
    assert "maximum 3 persons" in exc.value.detail

@pytest.mark.asyncio
async def test_annadhanam_meals_limit(mock_deps, mock_conn):
    mock_deps["srv"].return_value["name"] = "Annadhanam Meals"
    req = get_valid_request(num_persons=2) # Over 1 limit
    
    with pytest.raises(HTTPException) as exc:
        await booking_engine.create_booking(mock_conn, USER_ID, req)
    assert exc.value.status_code == 422
    assert "exactly 1 primary person" in exc.value.detail
