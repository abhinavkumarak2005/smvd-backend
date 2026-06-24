# Sri Manakula Vinayagar Devasthanam — Testing Plan

**Project:** Temple Booking Platform Backend  
**Team:** Abhinav · Athreyan  
**Tools:** pytest · pytest-asyncio · httpx · Locust · Postman  

---

## Table of Contents

1. [Testing Philosophy](#1-testing-philosophy)
2. [Test Environment Setup](#2-test-environment-setup)
3. [Unit Testing Strategy](#3-unit-testing-strategy)
4. [Integration Testing Strategy](#4-integration-testing-strategy)
5. [API Testing Strategy](#5-api-testing-strategy)
6. [Database Testing Strategy](#6-database-testing-strategy)
7. [Security Testing Strategy](#7-security-testing-strategy)
8. [Load Testing Strategy](#8-load-testing-strategy)
9. [Bug Fixing Workflow](#9-bug-fixing-workflow)
10. [Release Validation Process](#10-release-validation-process)
11. [Test Coverage Requirements](#11-test-coverage-requirements)

---

## 1. Testing Philosophy

| Principle | Practice |
|-----------|----------|
| **Test the business contract, not the implementation** | Test what the API returns, not how the code does it internally |
| **Zero overbooking is the hardest constraint** | Concurrent test under race condition is mandatory before production |
| **Unhappy paths matter as much as happy paths** | Every HTTP error code must be tested |
| **Mock external services** | Razorpay, SMS, email — never call real APIs in tests |
| **Tests must be repeatable** | No date-based logic that breaks tomorrow. Use `freezegun` or fixed dates |
| **Test isolation** | Each test creates its own data, tears it down after. No shared state |

---

## 2. Test Environment Setup

### 2.1 Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures, test client, mocks
├── unit/
│   ├── test_auth.py
│   ├── test_booking_engine.py
│   ├── test_conflict_checker.py
│   ├── test_chariot_rules.py
│   ├── test_moolavar_abishegam.py
│   ├── test_annadhanam.py
│   ├── test_ganapathy_homam.py
│   ├── test_e_undiyal.py
│   ├── test_payment_webhooks.py
│   ├── test_calendar.py
│   ├── test_notices.py
│   ├── test_services.py
│   └── test_admin_rbac.py
└── integration/
    ├── test_booking_full_flow.py
    ├── test_payment_full_flow.py
    ├── test_e_undiyal_flow.py
    ├── test_capacity_concurrency.py
    ├── test_admin_workflow.py
    └── test_notice_lifecycle.py
```

### 2.2 conftest.py — Shared Fixtures

Define in `tests/conftest.py`:

```python
# Test client pointing to FastAPI app
@pytest.fixture
def client() → TestClient:
    Returns FastAPI TestClient (synchronous — no real network calls)

# Mocked Supabase Auth responses
@pytest.fixture
def mock_supabase_auth():
    Mock httpx calls to Supabase Auth API
    Returns preconfigured devotee/admin tokens

# Mocked Razorpay client
@pytest.fixture
def mock_razorpay():
    Mock razorpay.Client.order.create() and payment.refund()
    Returns gateway_order_id = "order_TEST12345"

# Mocked SMS/Email (MSG91, Resend)
@pytest.fixture
def mock_notifications():
    Mock all notification_service calls — verify they were called, not actual sending

# Mocked DB — in-memory test database or asyncpg mock
@pytest.fixture
async def test_db():
    Use a separate Supabase test project or asyncpg mock

# JWT tokens for different roles
@pytest.fixture
def devotee_token() → str:
    Valid JWT with app_role="devotee", sub="user-uuid-001"

@pytest.fixture
def admin_token() → str:
    Valid JWT with app_role="admin", sub="admin-uuid-001"

@pytest.fixture
def super_admin_token() → str:
    Valid JWT with app_role="super_admin"

@pytest.fixture
def staff_token() → str:
    Valid JWT with app_role="staff"

# Sample data fixtures
@pytest.fixture
def sample_service() → dict:
    { id, name, category, price_paise, advance_booking_days, is_active, session }

@pytest.fixture
def sample_slot() → dict:
    { id, service_id, date, session, total_capacity=5, confirmed_count=0, pending_count=0 }

@pytest.fixture
def sample_booking() → dict:
    A confirmed booking record for testing
```

### 2.3 Running Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_booking_engine.py -v

# Run with coverage report
pytest tests/unit/ --cov=app --cov-report=html

# Run and stop on first failure
pytest tests/ -x

# Run tests matching a pattern
pytest tests/ -k "test_booking" -v

# Run with verbose output + show print statements
pytest tests/ -v -s
```

### 2.4 pytest.ini Configuration

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests (fast, no real DB)
    integration: Integration tests (requires test DB)
    security: Security-focused tests
    load: Load tests (slow, run separately)
```

---

## 3. Unit Testing Strategy

Unit tests are **fast, isolated, and mock all external dependencies** (DB, Razorpay, SMS, Auth).

### 3.1 test_auth.py — Authentication Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_otp_send_valid_phone` | `+919876543210` | 200, `{ message: "OTP sent" }` |
| `test_otp_send_invalid_phone` | `9876543210` (no +91) | 422 |
| `test_otp_send_invalid_format` | `abcdefgh` | 422 |
| `test_otp_verify_correct` | Valid OTP | 200, access_token + profile |
| `test_otp_verify_wrong_otp` | Wrong OTP | 401 |
| `test_otp_verify_expired_otp` | Expired OTP | 401 |
| `test_jwt_expired_token` | Expired JWT | 401 |
| `test_jwt_invalid_signature` | Tampered JWT | 401 |
| `test_jwt_missing_header` | No Authorization header | 401 |
| `test_role_guard_devotee_on_admin` | Devotee token → admin route | 403 |
| `test_role_guard_staff_on_admin` | Staff token → admin route | 403 |
| `test_role_guard_admin_on_admin` | Admin token → admin route | 200 |
| `test_role_guard_admin_on_super_admin` | Admin token → super_admin route | 403 |
| `test_role_guard_super_admin_on_super_admin` | Super admin → super_admin route | 200 |
| `test_otp_rate_limit` | 4 OTP requests in 10 min | 4th returns 429 |
| `test_admin_login_rate_limit` | 6 login attempts | 6th returns 429 |

### 3.2 test_booking_engine.py — Booking Creation Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_create_booking_success` | Valid service, future date, 1 person | 201, booking_reference, gateway_order_id |
| `test_booking_past_date` | Date = yesterday | 422, `ADVANCE_DAYS` |
| `test_booking_today_if_advance_0` | Today, advance_days=0 | 201 (allowed) |
| `test_booking_advance_days_violation` | Ganapathy Homam, 3 days advance, requires 5 | 422 |
| `test_booking_blocked_date` | Date in calendar with status=blocked | 409, `DATE_BLOCKED` |
| `test_booking_partial_date_allowed_service` | Partial date + service in allowlist | 201 |
| `test_booking_partial_date_not_allowed` | Partial date + service NOT in allowlist | 409, `DATE_BLOCKED` |
| `test_booking_inactive_service` | `is_active=False` | 404 |
| `test_booking_slot_full` | `confirmed+pending = total_capacity` | 409, `SLOT_FULL` |
| `test_booking_slot_at_capacity_minus_1` | One spot left | 201 |
| `test_booking_duplicate` | Same user, service, date, session | 409, `DUPLICATE_BOOKING` |
| `test_booking_different_user_same_slot` | Different user, same slot available | 201 (allowed if capacity) |
| `test_booking_num_persons_0` | num_persons=0 | 422 |
| `test_booking_num_persons_6` | num_persons=6 | 422 |
| `test_booking_persons_length_mismatch` | num_persons=2, persons array length=1 | 422 |
| `test_booking_no_auth` | No JWT | 401 |
| `test_booking_creates_audit_log` | Valid booking | audit_service called once |
| `test_booking_creates_payment_order` | Valid booking | payment_service.create_order called |

### 3.3 test_conflict_checker.py — Conflict Rules Tests

| Test | Scenario | Expected |
|------|---------|----------|
| `test_kaapu_sandhana_blocks_kavasam` | Kaapu booked → Kavasam request | ConflictResult(blocked=True) |
| `test_kavasam_blocks_kaapu_sandhana` | Kavasam booked → Kaapu request | ConflictResult(blocked=True) |
| `test_kaapu_vennai_blocks_kavasam` | Kaapu Vennai booked → Kavasam request | ConflictResult(blocked=True) |
| `test_no_conflict_different_date` | Kaapu on date A, Kavasam on date B | ConflictResult(blocked=False) |
| `test_thirukalyanam_blocks_morning_chariot` | Thirukalyanam booked → Chariot morning request | ConflictResult(blocked=True) |
| `test_thirukalyanam_does_not_block_evening_chariot` | Thirukalyanam booked → Chariot evening | ConflictResult(blocked=False) |
| `test_ganapathy_homam_requires_approval` | Ganapathy booked → Chariot request | ConflictResult(blocked=False, requires_approval=True) |
| `test_no_rules_for_service` | Service with no conflict rules | ConflictResult(blocked=False, requires_approval=False) |

### 3.4 test_chariot_rules.py — Chariot-Specific Tests

| Test | Scenario | Expected |
|------|---------|----------|
| `test_chariot_capacity_is_one` | First chariot booking for session | 201 |
| `test_second_chariot_same_session` | Second morning chariot | 409, `SLOT_FULL` |
| `test_chariot_morning_and_evening_separate` | Morning + Evening chariot same day | Both 201 |
| `test_gold_chariot_and_silver_chariot` | Gold morning + Silver morning | Two separate slots — both should succeed |

### 3.5 test_moolavar_abishegam.py

| Test | Input | Expected |
|------|-------|----------|
| `test_max_families_at_capacity` | 10 families booked | 11th → 409 SLOT_FULL |
| `test_persons_per_family_max` | 3 persons | 201 |
| `test_persons_per_family_over_max` | 4 persons | 422 |
| `test_family_booking_increment` | Each booking increments pending_count | Correct |

### 3.6 test_annadhanam.py

| Test | Input | Expected |
|------|-------|----------|
| `test_annadhanam_meals_single_person` | num_persons=1 | 201 |
| `test_annadhanam_meals_multiple_persons` | num_persons=2 | 422 |
| `test_annadhanam_prasadha_thonnai` | Normal booking | 201 |

### 3.7 test_payment_webhooks.py — Webhook Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_valid_webhook_signature` | Correct HMAC | 200, booking confirmed |
| `test_invalid_webhook_signature` | Wrong HMAC | 400, critical log |
| `test_webhook_payment_captured` | payment.captured event | booking=confirmed, slot=confirmed |
| `test_webhook_payment_failed` | payment.failed event | booking=payment_failed, slot released |
| `test_webhook_duplicate_captured` | Same order sent twice | 200, no second processing |
| `test_webhook_wrong_amount` | amount mismatch | reject + refund initiated |
| `test_webhook_e_undiyal_payment` | E-Undiyal order captured | e_undiyal_service.complete_donation called |
| `test_webhook_unknown_event` | Unknown event type | 200, silently ignored |
| `test_webhook_booking_confirmed_count` | After capture | confirmed_count=1, pending_count=0 |

### 3.8 test_e_undiyal.py — Donation Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_initiate_donation_valid` | ₹500 donation | 201, gateway_order_id, 80G message |
| `test_donation_minimum_amount` | ₹50 | 422 (below ₹100 minimum) |
| `test_donation_anonymous` | No JWT | 201 (guest donation works) |
| `test_donation_authenticated` | With JWT | 201, user_id saved |
| `test_e_undiyal_no_booking_table` | After donation | bookings table untouched |
| `test_complete_donation` | After webhook | status=success, cert=pending_details |
| `test_80g_notification_sent` | After payment | SMS with 80G message sent |

### 3.9 test_calendar.py

| Test | Input | Expected |
|------|-------|----------|
| `test_unset_date_is_open` | Date not in calendar | available=true |
| `test_blocked_date` | Date in calendar as blocked | 409 DATE_BLOCKED |
| `test_partial_date_allowed_service` | Partial + service in allowlist | available=true |
| `test_partial_date_blocked_service` | Partial + service NOT in allowlist | 409 DATE_BLOCKED |
| `test_admin_create_blocked_date` | POST /admin/calendar | date created |
| `test_admin_unblock_date` | DELETE /admin/calendar/{date} | date removed, available |

### 3.10 test_admin_rbac.py — Role-Based Access Tests

| Test | Role | Route | Expected |
|------|------|-------|----------|
| `test_no_auth_admin_route` | None | /admin/bookings | 401 |
| `test_devotee_admin_route` | devotee | /admin/bookings | 403 |
| `test_staff_reports` | staff | /admin/reports/dashboard | 200 |
| `test_staff_approve` | staff | /admin/bookings/{id}/approve | 403 |
| `test_admin_approve` | admin | /admin/bookings/{id}/approve | 200 |
| `test_admin_create_service` | admin | POST /admin/services | 403 |
| `test_super_admin_create_service` | super_admin | POST /admin/services | 201 |
| `test_admin_change_role` | admin | PATCH /admin/users/{id}/role | 403 |
| `test_super_admin_change_role` | super_admin | PATCH /admin/users/{id}/role | 200 |

---

## 4. Integration Testing Strategy

Integration tests use a **real test database** (Supabase dev project) and test the complete flow from HTTP request to database write.

### 4.1 test_booking_full_flow.py

```
Scenario: Complete booking lifecycle

Setup:
  - Seed a service in test DB
  - Create a slot_inventory record (capacity=5)
  - Generate a valid devotee JWT

Steps:
  1. POST /api/v1/bookings → HTTP 201
     Assert: booking status = pending_payment
     Assert: slot pending_count = 1
     Assert: payment record exists with status = initiated

  2. Simulate Razorpay webhook (payment.captured)
     Build valid HMAC signature
     POST /api/v1/webhooks/payment/razorpay → HTTP 200
     Assert: booking status = confirmed
     Assert: slot confirmed_count = 1, pending_count = 0
     Assert: payment status = success
     Assert: audit_log has "booking.created" + "payment.success" entries

  3. GET /api/v1/bookings/{booking_id}
     Assert: status = confirmed, persons list returned

Teardown:
  - Delete test booking, slot, service from test DB
```

### 4.2 test_capacity_concurrency.py

```
Scenario: Zero overbooking under concurrent load

Setup:
  - Create slot with total_capacity = 5
  - Generate 20 different devotee JWTs

Steps:
  - Launch 20 concurrent POST /api/v1/bookings requests (asyncio.gather)
  - All requests have different user_ids, same service + date + session

Assert:
  - Exactly 5 bookings created (HTTP 201)
  - Exactly 15 requests rejected (HTTP 409 SLOT_FULL)
  - slot_inventory.pending_count = 5 (never exceeds total_capacity)
  - No partial state (no slot with pending_count > 5)

This is THE most important test. Zero overbooking is non-negotiable.
```

### 4.3 test_payment_full_flow.py

```
Scenario: Payment failure then success

Step 1: Create booking → pending_payment
Step 2: Simulate payment.failed webhook
         Assert: booking = payment_failed
         Assert: slot pending_count decremented back to 0

Step 3: Create NEW booking for same slot → HTTP 201 (slot available again)
Step 4: Simulate payment.captured → booking = confirmed
         Assert: slot confirmed_count = 1

Scenario: Double webhook (idempotency)
Step 1: Create booking
Step 2: Simulate payment.captured → confirmed
Step 3: Simulate same payment.captured again → HTTP 200, no changes
         Assert: booking still = confirmed (not changed to pending again)
         Assert: slot confirmed_count still = 1 (not incremented again)
```

### 4.4 test_e_undiyal_flow.py

```
Scenario: E-Undiyal donation → certificate delivery → dispatch

Step 1: POST /api/v1/e-undiyal/initiate → 201
        Assert: transaction_reference starts with "SMV-EU-"
        Assert: bookings table untouched
        Assert: gateway_order_id returned

Step 2: Simulate payment.captured for E-Undiyal order
        Assert: e_undiyal_transaction status = success
        Assert: certificate_status = pending_details
        Assert: SMS with 80G notification triggered

Step 3: POST /api/v1/e-undiyal/{id}/certificate-preference
        Body: { donor_location_type: "domestic", donor_address: {...} }
        Assert: certificate_status = processing
        Assert: delivery_mode = courier
        Assert: 7-10 day SMS sent

Step 4: POST /admin/certificates/{id}/issue (admin JWT)
        Assert: certificate_status = ready
        Assert: certificate_number = "SMV-80G-YYYY-NNNN"
        Assert: donor SMS with download link sent

Step 5: POST /admin/certificates/{id}/dispatch
        Body: { courier_partner: "BlueDart", courier_tracking_id: "BD123456" }
        Assert: certificate_status = dispatched
        Assert: donor SMS with tracking number sent
```

---

## 5. API Testing Strategy

### 5.1 Postman Collection

Maintain a Postman collection: `SMVD Backend.postman_collection.json` in `tests/` folder.

**Collection Structure:**
```
SMVD Backend
├── Auth
│   ├── OTP Send
│   ├── OTP Verify
│   ├── Admin Login
│   └── Admin 2FA Verify
├── Public APIs
│   ├── Services List
│   ├── Availability Check
│   └── Notices List
├── Bookings
│   ├── Create Booking (happy path)
│   ├── Create Booking (slot full)
│   ├── Create Booking (duplicate)
│   ├── Create Booking (blocked date)
│   └── Get Booking
├── Payments
│   ├── Create Order
│   └── Simulate Webhook (payment.captured)
├── E-Undiyal
│   ├── Initiate Donation
│   ├── Submit Certificate Preference (local)
│   ├── Submit Certificate Preference (domestic)
│   └── Submit Certificate Preference (international)
└── Admin
    ├── Calendar Management
    ├── Booking Approvals
    ├── Notice Management
    ├── Reports Dashboard
    └── Certificate Management
```

### 5.2 Environment Variables in Postman

```
BASE_URL = http://localhost:8000
DEVOTEE_TOKEN = (populated after OTP verify)
ADMIN_TOKEN = (populated after admin 2FA)
TEST_SERVICE_ID = (from seed data)
TEST_BOOKING_ID = (from create booking response)
```

### 5.3 Pre-Request Scripts

In Postman, booking endpoints auto-generate the auth header from the `DEVOTEE_TOKEN` variable.

### 5.4 API Test Checklist for Every Endpoint

For each new endpoint:
- [ ] Happy path returns correct status code and response body
- [ ] Required field missing → 422
- [ ] Invalid field format → 422
- [ ] Unauthorized (no token) → 401
- [ ] Wrong role → 403
- [ ] Resource not found → 404
- [ ] Business rule violation → 409 with correct `code`

---

## 6. Database Testing Strategy

### 6.1 Migration Testing

For every migration:
```bash
# Apply migration
alembic upgrade head

# Verify: correct tables exist
SELECT table_name FROM information_schema.tables WHERE table_schema='public';

# Verify: correct column types
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'slot_inventory';

# Verify: constraints
SELECT constraint_name, constraint_type FROM information_schema.table_constraints
WHERE table_name = 'bookings';

# Test rollback
alembic downgrade -1
alembic upgrade head   # Must succeed after rollback + re-apply
```

### 6.2 audit_logs Insert-Only Verification

After running migrations:
```sql
-- Try to UPDATE an audit log row (should fail)
UPDATE audit_logs SET action = 'tampered' WHERE id = '<any-id>';
-- Expected: ERROR: permission denied for table audit_logs

-- Try to DELETE (should fail)
DELETE FROM audit_logs WHERE id = '<any-id>';
-- Expected: ERROR: permission denied for table audit_logs

-- INSERT should work
INSERT INTO audit_logs (action, entity_type, severity) VALUES ('test', 'test', 'info');
-- Expected: INSERT 0 1
```

### 6.3 RLS Verification

Test that RLS policies are active:
```sql
-- As devotee user: should only see own bookings
SET LOCAL jwt.claims.sub = 'devotee-user-uuid';
SELECT * FROM bookings;
-- Expected: only rows where user_id = 'devotee-user-uuid'

-- As devotee: should not see other users' bookings
-- Expected: zero rows for other user's booking_id
```

### 6.4 UNIQUE Constraint Verification

```sql
-- Test unique booking_reference
INSERT INTO bookings (booking_reference, ...) VALUES ('SMV-BK-20260801-001', ...);
INSERT INTO bookings (booking_reference, ...) VALUES ('SMV-BK-20260801-001', ...);
-- Second INSERT should fail: duplicate key value

-- Test unique gateway_order_id in payments
INSERT INTO payments (gateway_order_id, ...) VALUES ('order_TEST001', ...);
INSERT INTO payments (gateway_order_id, ...) VALUES ('order_TEST001', ...);
-- Should fail: duplicate key
```

---

## 7. Security Testing Strategy

### 7.1 Authentication and Authorization Tests

```bash
# Test: No token
curl http://localhost:8000/api/v1/bookings -X POST
# Expected: 401

# Test: Invalid token
curl -H "Authorization: Bearer invalid.jwt.token" http://localhost:8000/api/v1/bookings
# Expected: 401

# Test: Expired token
# (generate a JWT with exp=now()-1hour, sign with correct key)
# Expected: 401

# Test: Valid devotee token on admin route
curl -H "Authorization: Bearer <devotee_token>" http://localhost:8000/admin/bookings
# Expected: 403

# Test: Valid admin token on super_admin route
curl -H "Authorization: Bearer <admin_token>" -X POST http://localhost:8000/admin/services
# Expected: 403
```

### 7.2 SQL Injection Tests

Try SQL injection in all string inputs:
```bash
# In booking persons name field
{ "full_name": "'; DROP TABLE bookings; --", "star": "Aswini" }
# Expected: 422 or 201 with literal string stored (never executed)

# In availability query params
GET /api/v1/availability?service_id=' OR 1=1--&date=2026-08-01
# Expected: 422 (UUID validation fails) or safely handled

# In admin search
GET /admin/users/search?q=' OR '1'='1
# Expected: empty results, no SQL execution
```

### 7.3 Webhook Signature Bypass Test

```bash
# Test: Missing signature header
curl -X POST http://localhost:8000/api/v1/webhooks/payment/razorpay \
  -H "Content-Type: application/json" \
  -d '{"event": "payment.captured", ...}'
# Expected: 400

# Test: Wrong signature
curl -X POST http://localhost:8000/api/v1/webhooks/payment/razorpay \
  -H "X-Razorpay-Signature: wrongsignature" \
  -H "Content-Type: application/json" \
  -d '{"event": "payment.captured", ...}'
# Expected: 400, CRITICAL log written

# Test: Valid HMAC of wrong content
# Expected: 400
```

### 7.4 Static Code Analysis

```bash
# Run Bandit (Python security linter)
bandit -r app/ -f json -o bandit_report.json

# Pass criteria:
# No HIGH severity issues
# No CRITICAL severity issues
# MEDIUM issues reviewed and accepted

# Run detect-secrets
detect-secrets scan --all-files
# Expected: zero new secrets detected
```

### 7.5 Rate Limit Verification

```bash
# OTP rate limit: 3 per 10 minutes
for i in {1..4}; do
  curl -X POST http://localhost:8000/api/v1/auth/otp/send \
    -d '{"phone": "+919876543210"}'
done
# 4th request should return 429

# Admin login rate limit: 5 per 5 minutes
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/admin/login \
    -d '{"email":"admin@smvd.in","password":"wrong"}'
done
# 6th request: 429
```

### 7.6 CORS Test

```bash
# Request from non-allowed origin
curl -H "Origin: https://evil-site.com" \
     http://localhost:8000/api/v1/services
# Expected: No Access-Control-Allow-Origin header (or empty)
# Frontend would receive CORS error

# Request from allowed origin
curl -H "Origin: https://smvd.in" \
     http://localhost:8000/api/v1/services
# Expected: Access-Control-Allow-Origin: https://smvd.in
```

---

## 8. Load Testing Strategy

### 8.1 Tool: Locust

Install: `pip install locust`

Run: `locust -f tests/load/locustfile.py --host=http://localhost:8000`

### 8.2 Load Test Scenarios

**Scenario 1: Availability Check (Read-heavy)**
```
Users: 200 concurrent
Duration: 5 minutes
Endpoint: GET /api/v1/availability?service_id=<uuid>&date=2026-08-01

Pass Criteria:
- p50 latency < 50ms
- p95 latency < 150ms
- Error rate < 0.1%
```

**Scenario 2: Booking Creation (Write-heavy)**
```
Users: 50 concurrent (each user creates 1 booking)
Duration: 3 minutes
Slot capacity: 50 (all should succeed)

Pass Criteria:
- p95 latency < 300ms
- Error rate < 1%
- Exactly 50 bookings created in DB (verify)
```

**Scenario 3: Zero Overbooking Under Load (Critical)**
```
Users: 100 concurrent (each user creates 1 booking)
Slot capacity: 5 (only 5 should succeed)
Duration: Burst — all requests in 1 second

Pass Criteria:
- Exactly 5 bookings with status=pending_payment
- Exactly 95 requests return 409 SLOT_FULL
- slot_inventory.pending_count = 5 (not 6, not 7, not 100)
- ZERO overbooking tolerated
```

**Scenario 4: Webhook Processing**
```
Users: 30 concurrent
Duration: 2 minutes
Endpoint: POST /api/v1/webhooks/payment/razorpay (with valid HMAC)

Pass Criteria:
- p95 latency < 200ms (webhook must respond to Razorpay within 5s)
- Error rate 0%
```

**Scenario 5: Mixed Load (Production Simulation)**
```
30% — GET /api/v1/services (public)
30% — GET /api/v1/availability (public)
20% — POST /api/v1/bookings (authenticated)
10% — GET /api/v1/bookings (authenticated)
10% — GET /admin/reports/dashboard (admin)

Users: 100 concurrent
Duration: 10 minutes

Pass Criteria:
- p95 latency < 300ms
- Error rate < 1%
- No memory leaks (Railway memory flat after 10 min)
```

### 8.3 Load Test Execution Schedule

| Day | Test | Environment |
|-----|------|-------------|
| Day 11 | Zero overbooking concurrency test (20 users) | Local |
| Day 13 | Scenarios 1–4 (moderate load) | Staging |
| Day 14 | Full mixed load test (Scenario 5) | Staging |
| Day 14 | Zero overbooking under 100 concurrent requests | Staging |

### 8.4 Results Recording

After each load test, record:
```
Test Date: 
Environment: 
Scenario: 
Users: 
Duration: 
p50 latency: 
p95 latency: 
p99 latency: 
Error rate: 
Requests/sec: 
DB max connections: 
Zero overbooking verified: Yes/No
```

---

## 9. Bug Fixing Workflow

### Priority Classification

| Priority | Definition | SLA |
|----------|-----------|-----|
| P0 — Critical | Production down, data corruption, security breach, overbooking | Fix within 1 hour |
| P1 — High | Core booking flow broken, payment not processing | Fix within 4 hours |
| P2 — Medium | Admin feature broken, notification failing, report wrong | Fix within 24 hours |
| P3 — Low | UI text, non-critical admin feature, cosmetic | Fix in next sprint |

### Bug Fixing Process

```
1. Bug reported / discovered
   ↓
2. Reproduce the bug locally
   ↓
3. Write a failing test that reproduces the bug
   (Test must FAIL before fix, PASS after fix)
   ↓
4. Fix the bug
   ↓
5. Verify the test now passes
   ↓
6. Run full test suite to ensure no regressions
   pytest tests/unit/ -v
   ↓
7. Open PR with:
   - The failing → passing test
   - The fix
   - PR description: "Bug: <what it was>, Fix: <what was changed>"
   ↓
8. Code review → merge
   ↓
9. Deploy to staging → verify fix in staging
   ↓
10. Deploy to production
```

### Bug Report Template

```
**Bug ID:** BUG-{date}-{number}
**Severity:** P0 / P1 / P2 / P3
**Discovered:** {who discovered} via {test/staging/production}
**Description:** What is happening?
**Expected:** What should happen?
**Steps to Reproduce:**
  1. ...
  2. ...
**Environment:** Local / Staging / Production
**Error Log:**
  (paste stack trace or API response)
**Owner:** Abhinav / Athreyan
**Status:** Open / In Progress / Fixed / Verified
```

---

## 10. Release Validation Process

### Pre-Staging Release Checklist

Before merging to `staging`:
- [ ] All unit tests passing (`pytest tests/unit/ -v` → 0 failures)
- [ ] No new Bandit HIGH/CRITICAL issues
- [ ] No new secrets detected
- [ ] PR reviewed and approved by other developer
- [ ] Migration (if any) tested: upgrade + downgrade + re-upgrade

### Staging Validation Checklist

After deploying to staging:
- [ ] Health check: `GET https://staging-api.smvd.in/api/v1/health` → 200
- [ ] Services list returns 10 services
- [ ] OTP auth flow works end-to-end
- [ ] Booking creation works
- [ ] Simulated webhook confirms booking
- [ ] Admin login + 2FA works
- [ ] Admin booking approval works
- [ ] E-Undiyal donation + webhook works
- [ ] Certificate preference submission works
- [ ] Public notices returns active notices
- [ ] Reports dashboard returns data
- [ ] No 500 errors in Railway staging logs

### Pre-Production Release Checklist

Before merging to `main`:
- [ ] All staging validation items pass
- [ ] Integration tests pass on staging
- [ ] Load test results documented and within pass criteria
- [ ] Zero overbooking test passed
- [ ] Security checks passed (Bandit, detect-secrets, CORS, rate limits)
- [ ] Migration downgrade tested
- [ ] Rollback procedure ready (Railway prev deployment version noted)
- [ ] Temple admin has been briefed on new features
- [ ] Razorpay webhook URL updated to production URL (if changed)
- [ ] Production environment variables verified

### Production Go-Live Verification (Day 14)

After production deployment:
- [ ] Health check: `GET https://api.smvd.in/api/v1/health` → 200, `db: connected`
- [ ] `GET https://api.smvd.in/api/v1/services` → 10 services
- [ ] OTP send works with real phone number (smoke test)
- [ ] Admin login works in production
- [ ] Sentry dashboard shows test event received
- [ ] UptimeRobot monitor shows green
- [ ] No 500 errors in first 10 minutes

---

## 11. Test Coverage Requirements

| Module | Minimum Coverage |
|--------|-----------------|
| `app/services/booking_engine.py` | 85% |
| `app/services/conflict_checker.py` | 90% |
| `app/services/slot_service.py` | 80% |
| `app/services/webhook_service.py` | 85% |
| `app/services/e_undiyal_service.py` | 80% |
| `app/services/certificate_service.py` | 80% |
| `app/dependencies/auth.py` | 90% |
| `app/repositories/*.py` | 70% |
| **Overall Backend Coverage** | **75% minimum** |

### Generating Coverage Report

```bash
pytest tests/unit/ --cov=app --cov-report=html --cov-report=term-missing

# HTML report at: htmlcov/index.html
# Open in browser to see line-by-line coverage
```
