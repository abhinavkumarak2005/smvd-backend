import pytest
from fastapi.testclient import TestClient
from app.main import app

# TODO: Add full fixtures in Task 9.1 (Abhinav - Day 9)
# - Mock DB connection (asyncpg pool mock)
# - Mock Supabase Auth (httpx mock)
# - Mock Razorpay API (httpx mock)
# - Common fixtures: valid_devotee_token, valid_admin_token, sample_service, sample_slot

@pytest.fixture
def client():
    return TestClient(app)
