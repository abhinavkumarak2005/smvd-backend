import pytest
import json
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import date

from app.services.calendar_service import check_date

@pytest.mark.asyncio
async def test_calendar_blocked_date():
    mock_conn = AsyncMock()
    
    # Return a blocked date
    mock_conn.fetchrow.return_value = {
        "date": date(2026, 9, 1),
        "status": "blocked",
        "notes": "Festival day",
        "allowed_service_ids": "[]"
    }
    
    res = await check_date(mock_conn, date(2026, 9, 1), uuid4())
    assert res.status == "blocked"
    assert res.notes == "Festival day"

@pytest.mark.asyncio
async def test_calendar_partial_date_allowed_service():
    mock_conn = AsyncMock()
    service_id = uuid4()
    
    # Return a partial date with service_id allowed
    mock_conn.fetchrow.return_value = {
        "date": date(2026, 9, 1),
        "status": "partial",
        "notes": "VIP only",
        "allowed_service_ids": json.dumps([str(service_id)])
    }
    
    res = await check_date(mock_conn, date(2026, 9, 1), service_id)
    assert res.status == "open"

@pytest.mark.asyncio
async def test_calendar_partial_date_non_allowed_service():
    mock_conn = AsyncMock()
    allowed_service_id = uuid4()
    request_service_id = uuid4()
    
    # Return a partial date with some other service allowed
    mock_conn.fetchrow.return_value = {
        "date": date(2026, 9, 1),
        "status": "partial",
        "notes": "VIP only",
        "allowed_service_ids": json.dumps([str(allowed_service_id)])
    }
    
    res = await check_date(mock_conn, date(2026, 9, 1), request_service_id)
    assert res.status == "blocked"
    assert res.notes == "VIP only"
