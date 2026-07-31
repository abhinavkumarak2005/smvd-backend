import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role, CurrentUser

@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    # Basic fetchrow mock that can be overridden in tests
    conn.fetchrow.return_value = None
    conn.fetch.return_value = []
    conn.fetchval.return_value = None
    conn.execute.return_value = None
    
    # Allow async with conn.transaction()
    from unittest.mock import MagicMock
    tx_mock = AsyncMock()
    conn.transaction = MagicMock()
    conn.transaction.return_value.__aenter__.return_value = tx_mock
    conn.transaction.return_value.__aexit__.return_value = None
    return conn

@pytest.fixture
def client(mock_conn):
    # Override get_db to return our mock connection
    async def override_get_db():
        yield mock_conn
        
    app.dependency_overrides[get_db] = override_get_db
    
    # We will let individual tests override `require_role` if they need auth
    yield TestClient(app)
    
    app.dependency_overrides.clear()

@pytest.fixture
def auth_client(client):
    """Client authenticated as a standard devotee."""
    async def override_get_current_user():
        return CurrentUser(id="11111111-1111-1111-1111-111111111111", role="devotee")
        
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def admin_client(client):
    """Client authenticated as an admin."""
    async def override_get_current_user():
        return CurrentUser(id="22222222-2222-2222-2222-222222222222", role="super_admin")
        
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()
