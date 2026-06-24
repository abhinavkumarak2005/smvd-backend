# Sri Manakula Vinayagar Devasthanam — Abhinav Backend Tasks

**Developer:** Abhinav  
**Role:** Tech Lead / Core Backend  
**Period:** Day 1 – Day 14  
**Modules Owned:** Project Setup · Auth · Booking Engine · Conflict Rules · Slot Service · Payment · Webhook · Calendar · CI/CD

> Read `backend_master_plan.md` fully before starting Day 1.  
> Every task ends with a completion check. Do not move to next day until the check passes.

---

## Day 1 — Project Foundation & Infrastructure

**Focus:** Skeleton project, config, database connection, health check.  
**Estimated Effort:** 7 hours

### Tasks

#### 1.1 Repository Setup (1 hour)
- Create the GitHub repository: `smvd-backend`
- Set branch protection: `main` and `staging` branches require PR + 1 review
- Create base branches: `main`, `staging`
- Clone locally, initialize Python 3.11 virtual environment
- Create `.gitignore` (Python standard + `.env` files)

#### 1.2 Project Skeleton (1.5 hours)
Create the complete folder structure (see `backend_master_plan.md` Section 2):
```
smvd-backend/
app/
  main.py          ← empty FastAPI app
  config.py        ← Pydantic BaseSettings
  database.py      ← asyncpg pool setup
  routers/         ← empty __init__.py files
  services/        ← empty __init__.py files
  repositories/    ← empty __init__.py files
  models/db/       ← empty
  models/schemas/  ← empty
  dependencies/    ← empty
  middleware/      ← empty
  background/      ← empty
migrations/
tests/
  conftest.py
.env.example
requirements.txt
Dockerfile
```

**requirements.txt must include:**
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
asyncpg==0.29.0
pydantic==2.7.0
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
httpx==0.27.0
slowapi==0.1.9
APScheduler==3.10.4
WeasyPrint==62.3
razorpay==1.4.1
python-multipart==0.0.9
sentry-sdk[fastapi]==1.45.0
alembic==1.13.1
SQLModel==0.0.18
pytest==8.2.0
pytest-asyncio==0.23.6
bandit==1.7.8
```

#### 1.3 config.py (45 min)
Implement `Settings` class using Pydantic `BaseSettings`:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — For backend DB access
- `SUPABASE_ANON_KEY` — For Auth API calls
- `SUPABASE_JWT_SECRET` — For JWT verification
- `DATABASE_URL` — asyncpg connection string (PgBouncer port 6543)
- `RAZORPAY_KEY_ID` — Razorpay API key
- `RAZORPAY_KEY_SECRET` — Razorpay secret
- `RAZORPAY_WEBHOOK_SECRET` — Webhook HMAC key
- `MSG91_API_KEY` — SMS gateway
- `RESEND_API_KEY` — Email service
- `ENVIRONMENT` — `local` | `staging` | `production`
- `ALLOWED_ORIGINS` — Comma-separated list of allowed CORS origins
- `SENTRY_DSN` — Optional, for error tracking

All values load from `.env` file. No defaults for secrets.

#### 1.4 database.py (1 hour)
- Implement async connection pool using `asyncpg.create_pool()`
- Pool config: min_size=5, max_size=20, command_timeout=60
- Implement `get_db()` dependency (yields a connection from pool)
- Implement `init_db()` called at FastAPI startup event
- Implement `close_db()` called at FastAPI shutdown event
- Health check query: `SELECT 1`

#### 1.5 main.py (1 hour)
- Initialize FastAPI app with title, version, description
- Register CORS middleware (origins from `ALLOWED_ORIGINS` setting)
- Register rate limit middleware (slowapi)
- Register request logging middleware
- Add `@app.get("/api/v1/health")` route:
  ```
  Response: { "status": "ok", "environment": "local", "db": "connected", "version": "1.0.0" }
  ```
- Register `startup` and `shutdown` events for DB pool
- Register APScheduler jobs at startup

#### 1.6 .env.example (15 min)
Create `.env.example` with all keys listed, values as `"YOUR_VALUE_HERE"`.  
This is committed to repo. The real `.env` is never committed.

#### 1.7 Initial Commit + Branch Setup (30 min)
- Commit skeleton: `feat: project skeleton and config`
- Push `main` and `staging` branches
- Notify Athreyan: "Repo ready. Clone and run `pip install -r requirements.txt`. Get Supabase credentials from me."

---

### Day 1 Completion Criteria

- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `GET http://localhost:8000/api/v1/health` returns HTTP 200 with `{ "status": "ok" }`
- [ ] `GET http://localhost:8000/api/v1/health` shows `"db": "connected"` (Supabase connected)
- [ ] GitHub repo has `main` and `staging` branches with branch protection
- [ ] Athreyan has been given Supabase dev project credentials

---

## Day 2 — Authentication System

**Focus:** OTP-based auth, admin email login, JWT dependency, role guards.  
**Estimated Effort:** 7 hours  
**Dependency:** Day 1 complete, Athreyan's migrations must be done (coordinate)

### Tasks

#### 2.1 dependencies/auth.py (2 hours)

Implement the JWT verification dependency:

**Concept (not code):**
- `get_current_user(token)` — Verifies JWT, returns `CurrentUser(id, role)`
- `require_role(minimum_role)` — Factory that returns a dependency checking role hierarchy
- Role hierarchy order: `super_admin(4) > admin(3) > staff(2) > devotee(1)`
- If role < required → HTTP 403 `{ "detail": "Insufficient permissions" }`
- Cache Supabase JWKS (public keys) for 1 hour using `httpx`
- JWT decode: verify signature, expiry, issuer (Supabase project URL)

**Logic to implement:**
1. Extract `Authorization: Bearer <token>` header
2. Fetch JWKS from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
3. Decode JWT using `python-jose`
4. Extract `sub` (user_id), `app_metadata.role` (app_role)
5. Compare role against required minimum
6. Return `CurrentUser` or raise HTTPException

#### 2.2 models/schemas/auth.py (30 min)

Define Pydantic schemas:
- `OTPSendRequest` — `{ phone: str }` (validate E.164 format)
- `OTPVerifyRequest` — `{ phone: str, otp: str }`
- `AdminLoginRequest` — `{ email: EmailStr, password: str }`
- `AdminVerify2FARequest` — `{ session_token: str, totp_code: str }`
- `TokenResponse` — `{ access_token: str, refresh_token: str }`
- `UserProfile` — `{ id: UUID, phone: str, email: str | None, role: str, created_at: datetime }`

#### 2.3 routers/auth/otp.py (1.5 hours)

**POST /api/v1/auth/otp/send:**
- Validate phone (E.164 regex: `^\+[1-9]\d{1,14}$`)
- Rate limit: 3 requests per phone per 10 minutes (slowapi)
- Call Supabase Auth API: `POST {SUPABASE_URL}/auth/v1/otp`
  - Body: `{ "phone": phone, "channel": "sms" }`
  - Headers: `apikey: SUPABASE_ANON_KEY`
- Return: `{ "message": "OTP sent successfully" }`

**POST /api/v1/auth/otp/verify:**
- Call Supabase Auth API: `POST {SUPABASE_URL}/auth/v1/verify`
  - Body: `{ "type": "sms", "phone": phone, "token": otp }`
- On success: get `access_token`, `refresh_token`, `user.id`
- Check `users` table: `SELECT * FROM users WHERE id = user.id`
- If not found: INSERT new user `{ id, phone, role: 'devotee', created_at: now() }`
- Return: `{ access_token, refresh_token, profile }`

#### 2.4 routers/auth/login.py (1.5 hours)

**POST /api/v1/auth/admin/login:**
- Rate limit: 5 attempts per 5 minutes per IP
- Call Supabase Auth: `POST /auth/v1/token?grant_type=password`
- Verify JWT, extract `app_metadata.role`
- If role NOT IN `[admin, super_admin]` → 403
- Generate short-lived pre-2FA session token (valid 5 minutes)
- Return: `{ "session_token": "...", "message": "Enter your TOTP code" }`

**POST /api/v1/auth/admin/verify-2fa:**
- Validate session_token
- Verify TOTP code using `pyotp.TOTP(secret).verify(code)`
- If valid → return full admin JWT
- If invalid → 401 `{ "detail": "Invalid 2FA code" }`

**POST /api/v1/auth/refresh:**
- Accept refresh_token
- Call Supabase Auth: `POST /auth/v1/token?grant_type=refresh_token`
- Return new access_token

#### 2.5 middleware/rate_limit.py (30 min)
- Configure `slowapi` limiter with Redis backend
- Rate limit rules:
  - `/api/v1/auth/otp/send` → 3/10min per IP
  - `/api/v1/auth/admin/login` → 5/5min per IP
  - `/api/v1/bookings` (POST) → 10/hour per user
  - All other routes → 100/min per IP

#### 2.6 middleware/request_logging.py (30 min)
- Middleware that logs every request as JSON before and after processing
- Log: `{ request_id, method, path, user_id, status_code, duration_ms, ip }`
- Generate unique `request_id` (UUID) per request, add to response headers as `X-Request-ID`

#### 2.7 Register All Auth Routers in main.py (15 min)
- `app.include_router(otp_router, prefix="/api/v1/auth")`
- `app.include_router(login_router, prefix="/api/v1/auth")`

---

### Day 2 Completion Criteria

- [ ] `POST /api/v1/auth/otp/send` with valid phone → OTP arrives on phone
- [ ] `POST /api/v1/auth/otp/verify` with correct OTP → returns JWT tokens
- [ ] JWT token can be decoded and shows `app_role = "devotee"`
- [ ] `GET /api/v1/health` with invalid JWT → 401
- [ ] `require_role("admin")` dependency blocks devotee token → 403
- [ ] Admin login returns pre-2FA session token
- [ ] Rate limits working: send OTP 4 times in 10 min → 4th gets 429

---

## Day 3 — Booking Engine (Core Transaction)

**Focus:** The 10-step booking creation transaction.  
**Estimated Effort:** 8 hours  
**Dependency:** Day 2 auth complete, Athreyan's migrations must be done

### Tasks

#### 3.1 repositories/slot_repo.py (1 hour)

Implement the slot repository. All writes must be within an asyncpg transaction:

```
get_slot_for_update(service_id, date, session, conn)
  → SELECT ... FROM slot_inventory WHERE ... FOR UPDATE
  → Returns slot row or None

get_or_create_slot(service_id, date, session, total_capacity)
  → INSERT INTO slot_inventory (...) ON CONFLICT (service_id, date, session) DO NOTHING
  → SELECT ... FROM slot_inventory WHERE ...

increment_pending(slot_id, conn)
  → UPDATE slot_inventory SET pending_count = pending_count + 1 WHERE id = ?

decrement_pending(slot_id, conn)
  → UPDATE slot_inventory SET pending_count = pending_count - 1 WHERE id = ?

confirm_slot(slot_id, conn)
  → UPDATE slot_inventory SET confirmed_count = confirmed_count + 1, pending_count = pending_count - 1 WHERE id = ?
```

#### 3.2 repositories/booking_repo.py (1 hour)

```
create_booking(data, conn)
  → INSERT INTO bookings (...) RETURNING *

insert_persons(booking_id, persons, conn)
  → INSERT INTO booking_persons (...) for each person

check_duplicate(user_id, service_id, date, session, conn)
  → SELECT COUNT(*) FROM bookings WHERE ... AND status IN ('confirmed','pending_payment')
  → Returns bool

get_booking(booking_id)
  → SELECT bookings.*, booking_persons.* with JOIN

get_user_bookings(user_id, page, limit)
  → SELECT with pagination LIMIT/OFFSET
```

#### 3.3 services/calendar_service.py (45 min)

```
check_date(date, service_id) → DateStatus
  1. Query: SELECT * FROM calendar_dates WHERE date = ?
  2. If no row: return DateStatus(status="open")
  3. If status = "blocked": return DateStatus(status="blocked", notes=notes)
  4. If status = "partial":
     - Check if service_id in allowed_service_ids (JSONB array)
     - If yes: return DateStatus(status="open")
     - If no: return DateStatus(status="blocked", notes=notes)
```

#### 3.4 services/booking_engine.py (4 hours)

This is the most important file. Implement `create_booking(user_id, request)`:

```
STEP 1: Validate incoming schema (already done by Pydantic at router level)

STEP 2: calendar_service.check_date(request.date, request.service_id)
  → If blocked: raise HTTPException(409, "DATE_BLOCKED", ...)

STEP 3: service_repo.get_service(request.service_id)
  → If not found or not active: raise HTTPException(404)
  → Calculate min_booking_date = today + service.advance_booking_days
  → If request.date < min_booking_date: raise HTTPException(422, "ADVANCE_DAYS")

STEP 4: conflict_checker.check_conflicts(service_id, date, session)
  → If blocked: raise HTTPException(409, "CONFLICT_RULE", ...)
  → Capture requires_approval, notice_text

STEP 5–10: Open asyncpg transaction
  STEP 5: slot_repo.get_or_create_slot(service_id, date, session, capacity)
          slot_repo.get_slot_for_update(service_id, date, session, conn)
          If confirmed + pending >= total_capacity: ROLLBACK, raise 409 "SLOT_FULL"
          slot_repo.increment_pending(slot_id, conn)

  STEP 6: booking_repo.check_duplicate(user_id, service_id, date, session, conn)
          If duplicate: ROLLBACK, raise 409 "DUPLICATE_BOOKING"

  STEP 7: Apply special rules per service:
          Moolavar Abishegam: validate family count, persons per family
          Annadhanam Meals: assert num_persons == 1

  STEP 8: booking_repo.create_booking({...}, conn)
          booking_repo.insert_persons(booking_id, persons, conn)

  STEP 9: payment_service.create_order(booking_id, amount_paise)
          payment_repo.create_payment_record(booking_id, gateway_order_id, conn)

  STEP 10: COMMIT

Return: BookingResult(booking_id, reference, gateway_order_id, amount, requires_approval, notice)
```

#### 3.5 routers/bookings/create.py (45 min)

- Route: `POST /api/v1/bookings`
- Auth guard: `require_role("devotee")`
- Accept `BookingCreateRequest` schema
- Call `booking_engine.create_booking(current_user.id, request)`
- Add `BackgroundTask`: `audit_service.write_log("booking.created", ...)`
- Return HTTP 201 with `BookingResult`

#### 3.6 routers/bookings/status.py and list.py (30 min)

- `GET /api/v1/bookings/{booking_id}` → `booking_repo.get_booking(booking_id)`
  - Verify booking.user_id == current_user.id (or admin)
- `GET /api/v1/bookings` → `booking_repo.get_user_bookings(current_user.id, page, limit)`

---

### Day 3 Completion Criteria

- [ ] `POST /api/v1/bookings` creates booking with status=`pending_payment`
- [ ] Slot `pending_count` increments by 1 after booking
- [ ] Past date booking returns 422
- [ ] Advance days violation returns 422 with `ADVANCE_DAYS` code
- [ ] Slot at capacity returns 409 with `SLOT_FULL`
- [ ] Duplicate booking returns 409 with `DUPLICATE_BOOKING`
- [ ] Moolavar Abishegam with >3 persons per family returns 422
- [ ] Date in calendar as blocked returns 409 with `DATE_BLOCKED`

---

## Day 4 — Conflict Rules Engine

**Focus:** All 4 conflict rule types enforced dynamically from DB.  
**Estimated Effort:** 7 hours

### Tasks

#### 4.1 repositories/conflict_repo.py (30 min)

```
get_rules_for_service(service_id)
  → SELECT * FROM conflict_rules
    WHERE (service_a_id = service_id OR service_b_id = service_id)
    AND is_active = true
```

#### 4.2 services/conflict_checker.py (4 hours)

This reads rules from DB at runtime — fully data-driven.

```
check_conflicts(service_id, date, session, conn) → ConflictResult:

  1. rules = conflict_repo.get_rules_for_service(service_id)
  
  2. For each rule:
  
     RULE TYPE: mutual_exclusion (Kaapu ↔ Kavasam)
       → The other service is: if rule.service_a_id == service_id then service_b_id else service_a_id
       → Check: does a CONFIRMED or PENDING booking exist for the OTHER service
                on the same date? (any session)
       → If yes → return ConflictResult(blocked=True, message="Kaapu and Kavasam cannot be booked on the same date")

     RULE TYPE: session_exclusive (Chariot)
       → Both directions: check if service_id already has a CONFIRMED booking on same date+session
       → capacity=1 in slot_inventory handles this, but also check conflict_rules
       → If yes → return ConflictResult(blocked=True, message="Gold Chariot already booked for this session")

     RULE TYPE: a_blocks_b (Thirukalyanam blocks morning Chariot)
       → If service_id == service_b_id (Chariot morning) AND service_a (Thirukalyanam) has a confirmed booking
         on the same date → return ConflictResult(blocked=True, message="Thirukalyanam is scheduled for this date")

     RULE TYPE: requires_approval (Ganapathy Homam + Chariot)
       → If service_id == Chariot AND Ganapathy Homam has a booking on same date
       → ConflictResult(blocked=False, requires_approval=True, notice="Ganapathy Homam is scheduled...")

  3. If no rule triggered → ConflictResult(blocked=False, requires_approval=False)
```

**All 4 Conflict Scenarios to Test:**

| Scenario | Expected Result |
|----------|----------------|
| Book Kaapu, Kavasam already booked same date | HTTP 409 CONFLICT_RULE |
| Book Kavasam, Kaapu already booked same date | HTTP 409 CONFLICT_RULE |
| Book Gold Chariot morning, one already exists | HTTP 409 via SLOT_FULL (capacity=1) |
| Book Silver Chariot evening, one already exists | HTTP 409 via SLOT_FULL |
| Book morning Chariot when Thirukalyanam booked same date | HTTP 409 CONFLICT_RULE |
| Book Chariot when Ganapathy Homam on same date | HTTP 201 with requires_approval=true + notice |
| Book Ganapathy Homam < 5 days advance | HTTP 422 ADVANCE_DAYS |

#### 4.3 Seed conflict_rules in Migration (1 hour)

Work with Athreyan to ensure migration `011_seed_services_conflict_rules.py` inserts:
```
Service IDs for: Kaapu (Sandhana), Kaapu (Vennai), Kavasam,
                 Gold Chariot (morning), Gold Chariot (evening),
                 Silver Chariot (morning), Silver Chariot (evening),
                 Thirukalyanam, Ganapathy Homam

Conflict rules:
- Kaapu_Sandhana ↔ Kavasam: mutual_exclusion
- Kaapu_Vennai ↔ Kavasam: mutual_exclusion
- Gold_Chariot_morning → capacity=1 in slot_inventory
- Thirukalyanam blocks Gold_Chariot_morning: a_blocks_b
- Ganapathy_Homam + Chariot: requires_approval
```

#### 4.4 tests/unit/test_conflict_checker.py (1.5 hours)

Write unit tests for conflict_checker using pytest + mock DB:
- Test Kaapu/Kavasam mutual exclusion (both directions)
- Test Chariot session exclusivity
- Test Thirukalyanam blocks chariot
- Test Ganapathy Homam requires_approval
- Test no conflict when rules don't apply

---

### Day 4 Completion Criteria

- [ ] Booking Kaapu when Kavasam exists on same date → 409
- [ ] Booking Kavasam when Kaapu exists → 409
- [ ] Booking Chariot when capacity=1 slot full → 409
- [ ] Thirukalyanam + morning Chariot → 409
- [ ] Ganapathy Homam + Chariot → 201 with requires_approval=true
- [ ] Conflict rules tests: all passing in `pytest tests/unit/test_conflict_checker.py`
- [ ] Conflict rules work purely from DB rows (no hardcoded IDs in code)

---

## Day 5 — Payment Service

**Focus:** Razorpay order creation, payment model, integrate with booking engine.  
**Estimated Effort:** 7 hours

### Tasks

#### 5.1 repositories/payment_repo.py (45 min)

```
create_payment_record(booking_id, gateway_order_id, amount_paise, conn)
  → INSERT INTO payments (booking_id, gateway_order_id, amount_paise, status='initiated', currency='INR')

update_payment_status(gateway_order_id, status, gateway_payment_id)
  → UPDATE payments SET status=?, gateway_payment_id=? WHERE gateway_order_id=?

get_payment_by_order_id(gateway_order_id)
  → SELECT * FROM payments WHERE gateway_order_id = ?
```

#### 5.2 services/payment_service.py (1.5 hours)

```
create_order(booking_id, amount_paise) → { gateway_order_id, amount, currency }
  - Razorpay client.order.create({
      amount: amount_paise,
      currency: "INR",
      receipt: booking_id (truncated to 40 chars),
      notes: { booking_id: booking_id }
    })
  - Return: { gateway_order_id: order["id"], amount: amount_paise, currency: "INR" }
  - On Razorpay API error: raise HTTPException(503, "Payment service unavailable")

initiate_refund(payment_id, amount_paise) → { refund_id }
  - Razorpay client.payment.refund(payment_id, { amount: amount_paise })
  - Return: { refund_id: refund["id"] }
  - Log refund initiation to audit_log
```

#### 5.3 routers/payments/orders.py (1 hour)

**POST /api/v1/payments/create-order:**  
(Called by frontend after booking is created but before payment is made)
- Auth: `require_role("devotee")`
- Accept: `{ booking_id: UUID }`
- Verify: booking belongs to current user
- Verify: booking status == `pending_payment`
- If payment order already exists (idempotent): return existing order details
- If not: call `payment_service.create_order(booking_id, amount)`
- Return: `{ gateway_order_id, amount_paise, currency, razorpay_key_id }`

Note: `razorpay_key_id` is the public key sent to frontend to initialize Razorpay checkout. The secret is never sent.

#### 5.4 Integrate Payment into Booking Engine (30 min)

In `booking_engine.py` Step 9:
- After booking INSERT, call `payment_service.create_order(booking_id, service.price_paise)`
- Call `payment_repo.create_payment_record(booking_id, gateway_order_id, amount_paise, conn)`
- If Razorpay is unreachable: ROLLBACK entire booking transaction

#### 5.5 models/schemas/payment.py (30 min)

- `PaymentOrderResponse` — `{ gateway_order_id, amount_paise, currency, razorpay_key_id }`
- `PaymentStatusResponse` — `{ status, gateway_payment_id, paid_at }`

#### 5.6 Razorpay Test Mode Setup (30 min)

- Ensure `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are test-mode credentials
- Create a test order in Razorpay dashboard to verify connectivity
- Document test card numbers for use during testing

---

### Day 5 Completion Criteria

- [ ] `POST /api/v1/bookings` returns `gateway_order_id` in the response
- [ ] `POST /api/v1/payments/create-order` with valid booking_id returns Razorpay order
- [ ] Razorpay dashboard shows the test orders created
- [ ] Wrong booking owner attempting payment → 403
- [ ] Already-confirmed booking attempting payment → 409
- [ ] `payments` table has a record with `status=initiated` after booking creation

---

## Day 6 — Payment Webhook Handler

**Focus:** Razorpay webhook + full payment-to-confirmation flow.  
**Estimated Effort:** 7.5 hours

### Tasks

#### 6.1 services/webhook_service.py (2 hours)

```
verify_signature(raw_body: bytes, signature: str) → bool
  - expected = HMAC-SHA256(RAZORPAY_WEBHOOK_SECRET, raw_body)
  - Compare with signature header using secrets.compare_digest()
  - If mismatch: LOG CRITICAL "Webhook signature mismatch", return False

process_payment_captured(event_data: dict) → None
  Transactional:
  1. Extract order_id, payment_id, amount from event_data
  2. SELECT * FROM payments WHERE gateway_order_id=? FOR UPDATE
  3. If payment.status == 'success': log "duplicate webhook, skip" → RETURN (idempotent)
  4. SELECT * FROM bookings WHERE id=payment.booking_id FOR UPDATE
  5. Verify booking.status == 'pending_payment'
  6. Verify payment.amount_paise == event_data.amount (in paisa)
  7. SELECT * FROM slot_inventory WHERE ... FOR UPDATE (final capacity check)
  8. If over capacity: initiate refund, update booking status='rejected'
  9. Determine new status: requires_approval → 'pending_approval' else 'confirmed'
  10. UPDATE bookings SET status=new_status
  11. UPDATE slot_inventory: confirmed_count+=1, pending_count-=1
  12. UPDATE payments SET status='success', gateway_payment_id=payment_id, paid_at=NOW()
  COMMIT

process_payment_failed(event_data: dict) → None
  Transactional:
  1. SELECT * FROM payments WHERE gateway_order_id=?
  2. UPDATE payments SET status='failed'
  3. SELECT * FROM slot_inventory WHERE ... FOR UPDATE
  4. slot_repo.decrement_pending(slot_id, conn)
  5. UPDATE bookings SET status='payment_failed'
  COMMIT
```

#### 6.2 routers/payments/webhooks.py (1.5 hours)

**POST /api/v1/webhooks/payment/razorpay:**
- Read raw request body (not parsed JSON)
- Extract `X-Razorpay-Signature` header
- Call `webhook_service.verify_signature(raw_body, signature)`
- If invalid → HTTP 400, log CRITICAL
- Parse JSON body
- Route by event type:
  - `payment.captured` → `webhook_service.process_payment_captured(event)`
  - `payment.failed` → `webhook_service.process_payment_failed(event)`
  - Others → log and return 200 (ignore unknown events)
- Add BackgroundTasks:
  - On captured: `receipt_service.generate_pdf(booking_id)`, `notification_service.send_sms(phone, "Booking confirmed")`, `audit_service.write_log("payment.success")`
  - On failed: `notification_service.send_sms(phone, "Payment failed")`, `audit_service.write_log("payment.failed")`
- Return HTTP 200 OK (within 5 seconds — Razorpay requirement)

#### 6.3 services/audit_service.py (30 min)

```
write_log(action, entity_type, entity_id, actor_id, before_state, after_state, ip, user_agent) → None
  INSERT INTO audit_logs (action, entity_type, entity_id, actor_id, before_state, after_state, ip, user_agent, created_at=NOW())

Always called as FastAPI BackgroundTask, never awaited in main flow.
```

#### 6.4 services/notification_service.py (1 hour)

```
send_sms(phone: str, message: str) → None
  POST to MSG91 API with API key and phone
  Log success or failure at INFO/WARNING level
  Never raise exception (fire-and-forget)

send_email(to: str, subject: str, html_body: str) → None
  POST to Resend API: { from, to, subject, html }
  Log success or failure
  Never raise exception
```

#### 6.5 End-to-End Payment Test (1 hour)

Use Razorpay test mode to simulate full flow:
1. `POST /api/v1/bookings` → get `gateway_order_id`
2. Simulate Razorpay payment completion → manually trigger webhook with valid signature
3. Verify booking status → `confirmed`
4. Verify slot `confirmed_count` = 1, `pending_count` = 0
5. Verify receipt PDF created in Supabase Storage
6. Verify SMS/Email notification sent

---

### Day 6 Completion Criteria

- [ ] Valid webhook with `payment.captured` → booking becomes `confirmed`
- [ ] Valid webhook for `payment.failed` → booking becomes `payment_failed`, slot released
- [ ] Invalid HMAC signature → 400, critical log written
- [ ] Duplicate webhook (same order) → silently skipped (idempotent)
- [ ] `slot_inventory.confirmed_count` = 1 after successful payment
- [ ] `slot_inventory.pending_count` = 0 after confirmation
- [ ] Audit log entry created for payment success
- [ ] Webhook responds within 5 seconds

---

## Day 7 — Calendar Management System

**Focus:** Admin calendar API — date blocking, partial allow, advance notice.  
**Estimated Effort:** 6 hours

### Tasks

#### 7.1 repositories/calendar_repo.py (1 hour)

```
get_date(date) → CalendarDate | None
  SELECT * FROM calendar_dates WHERE date = ?

upsert_date(date, status, allowed_service_ids, notes) → CalendarDate
  INSERT INTO calendar_dates (...) ON CONFLICT (date) DO UPDATE SET ...

delete_date(date) → None
  DELETE FROM calendar_dates WHERE date = ?

get_date_range(start_date, end_date) → list[CalendarDate]
  SELECT * FROM calendar_dates WHERE date BETWEEN ? AND ? ORDER BY date
```

#### 7.2 routers/admin/calendar.py (2 hours)

All routes require `require_role("admin")`.

```
GET    /admin/calendar?start=2026-08-01&end=2026-08-31
  → calendar_repo.get_date_range(start, end)
  → Return list of configured dates (unlisted dates = open by default)

GET    /admin/calendar/{date}
  → calendar_repo.get_date(date)
  → If not found: return default { status: "open" }

POST   /admin/calendar/{date}
  Body: { status: "blocked" | "partial", notes: str, allowed_service_ids: [uuid] }
  → Validate: if status="partial", allowed_service_ids must not be empty
  → calendar_repo.upsert_date(date, status, allowed_service_ids, notes)
  → BackgroundTask: audit_service.write_log("calendar.date_updated", ...)
  → Return: updated CalendarDate

DELETE /admin/calendar/{date}
  → calendar_repo.delete_date(date)
  → Background: audit_log
  → Returns: 204 No Content

GET    /admin/calendar/export?start=?&end=?
  → Fetch range, format as JSON/CSV, return downloadable file
```

#### 7.3 routers/public/availability.py — Update (30 min)

Ensure the public availability endpoint uses `calendar_service.check_date()` correctly. Test with a blocked date.

#### 7.4 models/schemas/admin.py — Calendar schemas (30 min)

```
CalendarDateCreateRequest: { status, notes, allowed_service_ids }
CalendarDateResponse: { date, status, notes, allowed_service_ids, updated_at }
```

---

### Day 7 Completion Criteria

- [ ] `POST /admin/calendar/2026-09-01` with status=blocked → date is blocked
- [ ] `GET /api/v1/availability?date=2026-09-01` → `{ available: false, reason: "BLOCKED" }`
- [ ] Booking request for blocked date → 409 DATE_BLOCKED
- [ ] `POST /admin/calendar` with status=partial + 2 service IDs → partial works
- [ ] Service not in partial allowlist → 409 DATE_BLOCKED
- [ ] Service in partial allowlist → booking allowed
- [ ] Audit log entry for every calendar change

---

## Day 8 — Background Jobs

**Focus:** Slot cleanup job, notice scheduler, health monitoring.  
**Estimated Effort:** 5 hours

### Tasks

#### 8.1 background/slot_cleanup.py (2 hours)

```
cleanup_expired_bookings():
  Every 5 minutes:
  1. SELECT * FROM bookings
     WHERE status = 'pending_payment'
       AND created_at < NOW() - INTERVAL '15 minutes'
     LIMIT 100
  
  2. For each booking:
     a. BEGIN TRANSACTION
     b. SELECT * FROM slot_inventory WHERE ... FOR UPDATE
     c. slot_repo.decrement_pending(slot_id, conn)
     d. UPDATE bookings SET status = 'expired'
     e. UPDATE payments SET status = 'expired' (if exists)
     f. COMMIT
     g. audit_service.write_log("booking.expired", ...)
  
  3. Log: "Cleaned up N expired bookings"
```

#### 8.2 background/notice_scheduler.py (1 hour)

```
update_notice_statuses():
  Every 5 minutes:
  1. Activate: UPDATE notices SET status='active'
     WHERE status='scheduled' AND published_at <= NOW()
  
  2. Expire: UPDATE notices SET status='expired'
     WHERE status='active' AND expires_at < NOW()
  
  3. Log count of activated and expired notices
```

#### 8.3 Register Jobs in main.py (1 hour)

```
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(slot_cleanup.cleanup_expired_bookings, 'interval', minutes=5)
scheduler.add_job(notice_scheduler.update_notice_statuses, 'interval', minutes=5)
scheduler.add_job(metrics_snapshot, 'cron', hour=0, minute=5)

@app.on_event("startup")
async def startup():
    await init_db()
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    await close_db()
    scheduler.shutdown()
```

#### 8.4 Test Background Jobs (1 hour)

- Create a booking → wait 16 minutes (or manually set `created_at` 16 minutes ago in DB)
- Trigger `cleanup_expired_bookings()` manually
- Verify: booking status = `expired`, pending_count decremented
- Verify: creating a notice with `published_at` = 1 minute ago → trigger scheduler → notice is active

---

### Day 8 Completion Criteria

- [ ] Expired pending_payment bookings (>15 min) are set to `expired`
- [ ] Slot `pending_count` decremented when booking expires
- [ ] Notices with past `published_at` become active on scheduler run
- [ ] Notices past `expires_at` become `expired`
- [ ] Scheduler visible in application startup logs

---

## Day 9 — Unit Tests: Auth + Booking Engine + Conflicts

**Focus:** Full unit test suite for owned modules.  
**Estimated Effort:** 7 hours

### 9.1 tests/conftest.py
- FastAPI TestClient setup
- Mock DB connection (asyncpg pool mock)
- Mock Supabase Auth (httpx mock)
- Mock Razorpay API (httpx mock)
- Common fixtures: valid_devotee_token, valid_admin_token, sample_service, sample_slot

### 9.2 tests/unit/test_auth.py
- Valid OTP verify → returns tokens
- Invalid OTP → 401
- Expired JWT → 401
- Devotee token on admin route → 403
- Admin token on admin route → 200
- OTP rate limit exceeded → 429

### 9.3 tests/unit/test_booking_engine.py
- Successful booking → status=pending_payment, gateway_order_id present
- Past date → 422
- Advance days violation → 422
- Blocked date → 409 DATE_BLOCKED
- Slot full → 409 SLOT_FULL
- Duplicate booking → 409 DUPLICATE_BOOKING
- Moolavar Abishegam: 4 persons/family → 422
- Annadhanam Meals: 2 persons → 422

### 9.4 tests/unit/test_conflict_checker.py
- Kaapu + Kavasam both directions → 409
- Chariot session exclusivity (slot capacity=1)
- Thirukalyanam blocks morning chariot
- Ganapathy Homam + Chariot → requires_approval=true
- No conflict when rules don't match → passes through

---

### Day 9 Completion Criteria

- [ ] `pytest tests/unit/test_auth.py` → all tests pass
- [ ] `pytest tests/unit/test_booking_engine.py` → all tests pass
- [ ] `pytest tests/unit/test_conflict_checker.py` → all tests pass
- [ ] Test coverage > 80% for booking_engine.py and conflict_checker.py

---

## Day 10 — Unit Tests: Payment + Webhook + Capacity

**Estimated Effort:** 7 hours

### 10.1 tests/unit/test_payment_webhooks.py
- Valid HMAC signature → 200, booking confirmed
- Invalid HMAC signature → 400, critical log
- Duplicate webhook (already confirmed) → 200 (idempotent, no changes)
- payment.captured with wrong amount → reject + refund initiated
- payment.failed → booking=payment_failed, slot released

### 10.2 tests/unit/test_chariot_rules.py
- Only 1 chariot booking per session (morning/evening)
- Two morning chariot requests → first succeeds, second fails
- Morning and evening chariot on same day → both succeed (different sessions)

### 10.3 tests/unit/test_moolavar_abishegam.py
- 10 families booking → all 10 succeed
- 11th family booking → 409 SLOT_FULL
- 3 persons per family → valid
- 4 persons per family → 422

### 10.4 tests/unit/test_annadhanam.py
- Annadhanam Meals with 1 person → valid
- Annadhanam Meals with 2 persons → 422

### 10.5 tests/unit/test_calendar.py
- Blocked date → 409 DATE_BLOCKED
- Partial date: allowed service → booking works
- Partial date: non-allowed service → 409

---

### Day 10 Completion Criteria

- [ ] `pytest tests/unit/` → all tests pass (zero failures)
- [ ] Payment idempotency verified
- [ ] Concurrency test: 2 simultaneous requests for capacity=1 → exactly 1 succeeds

---

## Day 11 — Integration Tests: Full Booking + Payment Flow

**Estimated Effort:** 7 hours

### 11.1 tests/integration/test_booking_full_flow.py

Full end-to-end test using test database:
1. Create service in DB
2. Create slot_inventory record
3. OTP verify → get token
4. POST /api/v1/bookings → get booking_id + gateway_order_id
5. Simulate Razorpay webhook (payment.captured with valid HMAC)
6. Verify booking status = confirmed
7. Verify slot confirmed_count = 1
8. Verify audit_logs has entries for booking.created + payment.success
9. Verify receipt PDF uploaded to Supabase Storage

### 11.2 tests/integration/test_capacity_concurrency.py

Concurrency test:
- Set slot capacity = 5
- Fire 20 simultaneous POST /api/v1/bookings requests (asyncio.gather)
- Verify: exactly 5 bookings created (SLOT_FULL for the other 15)
- Verify: slot_inventory.pending_count = 5 (never > 5)

### 11.3 tests/integration/test_payment_full_flow.py

- Create booking
- Payment failure webhook → verify booking=payment_failed, slot released
- Create new booking for same slot → succeeds (slot available again)
- Payment success webhook → confirmed

---

### Day 11 Completion Criteria

- [ ] Full booking→payment→confirmation integration test passes
- [ ] Concurrency test: exactly 5 confirmed for capacity=5 under 20 concurrent requests
- [ ] Zero overbooking verified via concurrent test
- [ ] All audit_log entries present

---

## Day 12 — Security Hardening

**Estimated Effort:** 5 hours

### 12.1 Rate Limiting Review
- Verify all rate limits are in place and correct
- Test OTP: 4th request in 10 min → 429
- Test admin login: 6th attempt → 429
- Test booking: 11th booking in 1 hour → 429

### 12.2 CORS Verification
- `ALLOWED_ORIGINS` must not contain `*` in staging/prod
- Test cross-origin request from non-allowed domain → blocked

### 12.3 Input Validation Review
- Test all endpoints with SQL injection payloads → all sanitized (parameterized queries)
- Test oversized payloads → 422
- Test missing required fields → 422

### 12.4 Webhook Security
- Rotate webhook secret in Razorpay test dashboard
- Verify old secret → 400 (old HMAC fails)
- Register new secret in env → webhook works again

### 12.5 No Secrets in Code Audit
- Run `detect-secrets scan --all-files` → zero findings
- Verify `.env` is in `.gitignore` and not in any commit

---

### Day 12 Completion Criteria

- [ ] Bandit scan: no HIGH or CRITICAL issues
- [ ] detect-secrets: zero findings
- [ ] SQL injection attempts → all return 422/400 (not 500)
- [ ] CORS blocked for non-allowed origins
- [ ] Rate limits all verified

---

## Day 13 — Staging Deployment + CI/CD

**Estimated Effort:** 7 hours

### 13.1 Dockerfile (1 hour)
- Multi-stage Docker build
- Stage 1: Install dependencies
- Stage 2: Copy app code, set CMD
- Non-root user in container

### 13.2 GitHub Actions — CI Pipeline (1.5 hours)

`.github/workflows/ci.yml`:
- Trigger: push to any branch
- Jobs: pytest, bandit, detect-secrets
- Fail fast: any job failure blocks PR merge

### 13.3 GitHub Actions — Staging Deploy (1.5 hours)

`.github/workflows/staging.yml`:
- Trigger: merge to `staging` branch
- Steps: run CI → Alembic migrate staging DB → Railway deploy → health check

### 13.4 Railway Setup — Staging (1 hour)
- Create Railway project: `smvd-backend-staging`
- Set all environment variables from `.env.example`
- Set `ENVIRONMENT=staging`
- Set Railway custom domain: `staging-api.smvd.in` (or similar)
- Deploy manually first → verify health check

### 13.5 Staging Smoke Test (2 hours)

Run through full flow on staging:
1. OTP send + verify
2. Create booking
3. Simulate webhook
4. Verify confirmation
5. Check admin login + 2FA

---

### Day 13 Completion Criteria

- [ ] Staging URL returns 200 on health check
- [ ] GitHub Actions CI runs on every PR
- [ ] Staging CI/CD pipeline runs on merge to staging
- [ ] All staging smoke tests pass
- [ ] Staging Supabase DB has all tables and seed data

---

## Day 14 — Load Test + Production Deployment

**Estimated Effort:** 7 hours

### 14.1 Load Testing with Locust (2 hours)

```
locustfile.py scenarios:
- CheckAvailability: 100 users, 1min
- CreateBooking: 50 users, 2min (slot capacity=50)
- WebhookSimulation: 30 users, 1min

Pass criteria:
- p95 latency < 300ms
- Error rate < 1%
- Zero overbooking on concurrent slot capacity test
```

### 14.2 Production Railway Setup (1.5 hours)
- Create Railway project: `smvd-backend-production`
- Set all production environment variables
- `ENVIRONMENT=production`
- `SENTRY_DSN=<production DSN>`
- Production Supabase project credentials
- Production Razorpay live mode keys
- Custom domain: `api.smvd.in`

### 14.3 Production Deployment (1 hour)
- Run `alembic upgrade head` on production DB
- Deploy via Railway (trigger from GitHub Actions on merge to `main`)
- Health check: `GET https://api.smvd.in/api/v1/health` → 200

### 14.4 Post-Deployment Verification (1 hour)
- Run production smoke tests (OTP + booking + webhook)
- Verify Sentry receiving events
- Verify UptimeRobot monitor active
- Verify Razorpay webhook URL points to production
- Verify admin 2FA works in production

### 14.5 Production Checklist Sign-off

Go through every item in `backend_master_plan.md` Section 14 and check each item.

---

### Day 14 Completion Criteria

- [ ] Load test: p95 < 300ms, error rate < 1%, zero overbooking
- [ ] `GET https://api.smvd.in/api/v1/health` returns 200
- [ ] Full booking flow works in production
- [ ] Admin login + 2FA works in production
- [ ] Sentry showing events
- [ ] Production checklist 100% complete

---

## Summary: Abhinav Module Ownership

| Module | Files | Days |
|--------|-------|------|
| Project Setup | main.py, config.py, database.py, requirements.txt | Day 1 |
| Auth System | auth/, dependencies/auth.py, middleware/ | Day 2 |
| Booking Engine | services/booking_engine.py, routers/bookings/ | Day 3 |
| Conflict Rules | services/conflict_checker.py | Day 4 |
| Payment Service | services/payment_service.py, routers/payments/ | Day 5 |
| Webhook Handler | services/webhook_service.py, routers/payments/webhooks.py | Day 6 |
| Calendar Management | services/calendar_service.py, routers/admin/calendar.py | Day 7 |
| Background Jobs | background/slot_cleanup.py, notice_scheduler.py | Day 8 |
| Unit Tests (core) | tests/unit/test_auth, booking, conflict, payment | Days 9–10 |
| Integration Tests | tests/integration/ | Day 11 |
| Security Hardening | middleware, rate limits, CORS | Day 12 |
| CI/CD + Deployment | Dockerfile, GitHub Actions, Railway | Days 13–14 |
