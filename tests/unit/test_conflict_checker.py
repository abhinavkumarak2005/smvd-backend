import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.services import conflict_checker

# Dummy UUIDs
KAAPU_ID = uuid4()
KAVASAM_ID = uuid4()
CHARIOT_ID = uuid4()
THIRUKALYANAM_ID = uuid4()
HOMAM_ID = uuid4()

def get_dummy_rule(rule_type, s_a, s_b, direction="a_to_b", notice="Conflict"):
    return {
        "rule_type": rule_type,
        "service_a_id": str(s_a),
        "service_b_id": str(s_b),
        "direction": direction,
        "notice_text": notice
    }

@pytest.mark.asyncio
async def test_kaapu_kavasam_conflict(monkeypatch, mock_conn):
    # Rule: mutual_exclusion
    rules = [get_dummy_rule("mutual_exclusion", KAAPU_ID, KAVASAM_ID, "bidirectional", "Cannot book both")]
    
    async def mock_get_rules(*args, **kwargs):
        return rules
        
    async def mock_has_booking(*args, **kwargs):
        return True # Simulate the other service is booked

    monkeypatch.setattr("app.repositories.conflict_repo.get_rules_for_service", mock_get_rules)
    monkeypatch.setattr("app.services.conflict_checker._has_booking_for_service", mock_has_booking)

    # Test direction 1: Booking Kaapu, Kavasam already booked
    target_date = datetime.now(timezone.utc).date()
    res1 = await conflict_checker.check_conflicts(mock_conn, KAAPU_ID, target_date, "morning")
    assert res1.blocked is True
    assert res1.message == "Cannot book both"
    
    # Test direction 2: Booking Kavasam, Kaapu already booked
    res2 = await conflict_checker.check_conflicts(mock_conn, KAVASAM_ID, target_date, "morning")
    assert res2.blocked is True
    assert res2.message == "Cannot book both"

@pytest.mark.asyncio
async def test_thirukalyanam_blocks_chariot(monkeypatch, mock_conn):
    # Rule: a_blocks_b (Thirukalyanam blocks Chariot)
    rules = [get_dummy_rule("a_blocks_b", THIRUKALYANAM_ID, CHARIOT_ID, "a_to_b", "Chariot blocked by Thirukalyanam")]
    
    async def mock_get_rules(*args, **kwargs):
        return rules
        
    async def mock_has_booking(conn, s_id, d, *args, **kwargs):
        # Only Thirukalyanam is booked
        return s_id == THIRUKALYANAM_ID

    monkeypatch.setattr("app.repositories.conflict_repo.get_rules_for_service", mock_get_rules)
    monkeypatch.setattr("app.services.conflict_checker._has_booking_for_service", mock_has_booking)

    target_date = datetime.now(timezone.utc).date()
    
    # Booking Chariot should be blocked
    res1 = await conflict_checker.check_conflicts(mock_conn, CHARIOT_ID, target_date, "morning")
    assert res1.blocked is True
    assert res1.message == "Chariot blocked by Thirukalyanam"
    
    # Booking Thirukalyanam should NOT be blocked (it's the blocker)
    res2 = await conflict_checker.check_conflicts(mock_conn, THIRUKALYANAM_ID, target_date, "morning")
    assert res2.blocked is False

@pytest.mark.asyncio
async def test_ganapathy_homam_chariot_warning(monkeypatch, mock_conn):
    # Rule: requires_approval
    rules = [get_dummy_rule("requires_approval", HOMAM_ID, CHARIOT_ID, "bidirectional", "Requires admin approval for both")]
    
    async def mock_get_rules(*args, **kwargs):
        return rules
        
    async def mock_has_booking(*args, **kwargs):
        return True # The other service is booked

    monkeypatch.setattr("app.repositories.conflict_repo.get_rules_for_service", mock_get_rules)
    monkeypatch.setattr("app.services.conflict_checker._has_booking_for_service", mock_has_booking)

    target_date = datetime.now(timezone.utc).date()
    
    res = await conflict_checker.check_conflicts(mock_conn, HOMAM_ID, target_date, "morning")
    assert res.blocked is False
    assert res.requires_approval is True
    assert res.notice == "Requires admin approval for both"

@pytest.mark.asyncio
async def test_no_conflict(monkeypatch, mock_conn):
    # Rule exists but no existing booking
    rules = [get_dummy_rule("mutual_exclusion", KAAPU_ID, KAVASAM_ID)]
    
    async def mock_get_rules(*args, **kwargs):
        return rules
        
    async def mock_has_booking(*args, **kwargs):
        return False # No bookings exist

    monkeypatch.setattr("app.repositories.conflict_repo.get_rules_for_service", mock_get_rules)
    monkeypatch.setattr("app.services.conflict_checker._has_booking_for_service", mock_has_booking)

    target_date = datetime.now(timezone.utc).date()
    
    res = await conflict_checker.check_conflicts(mock_conn, KAAPU_ID, target_date, "morning")
    assert res.blocked is False
    assert res.requires_approval is False
