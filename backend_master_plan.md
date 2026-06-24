# Sri Manakula Vinayagar Devasthanam — Backend Master Plan

**Project:** Temple Booking Platform  
**Version:** 1.0 | **Date:** June 2026  
**Team:** Abhinav (Lead) · Athreyan  
**Stack:** FastAPI · Supabase PostgreSQL · Supabase Auth · Razorpay · Railway  

---

## Table of Contents

1. [Project Overview & Principles](#1-project-overview--principles)
2. [Complete Folder Structure](#2-complete-folder-structure)
3. [Request-to-Response Workflow](#3-request-to-response-workflow)
4. [Module Interactions](#4-module-interactions)
5. [Database Flow](#5-database-flow)
6. [Authentication & Authorization Flow](#6-authentication--authorization-flow)
7. [Service Layer Responsibilities](#7-service-layer-responsibilities)
8. [Repository Layer Responsibilities](#8-repository-layer-responsibilities)
9. [Validation Strategy](#9-validation-strategy)
10. [Error Handling Strategy](#10-error-handling-strategy)
11. [Logging Strategy](#11-logging-strategy)
12. [Background Jobs](#12-background-jobs)
13. [Deployment Flow](#13-deployment-flow)
14. [Production Readiness Requirements](#14-production-readiness-requirements)
15. [Module Ownership Map](#15-module-ownership-map)
16. [14-Day Milestone Overview](#16-14-day-milestone-overview)

---

## 1. Project Overview & Principles

The Sri Manakula Vinayagar Devasthanam backend is a **production-grade temple booking and operations platform**.

### Non-Negotiable Principles

| Principle | Practical Meaning |
|-----------|------------------|
| **Backend is the only source of truth** | Frontend sends intent only. All prices, capacities, and conflict rules come from the database — never from the client |
| **Zero overbooking** | All slot writes use `SELECT FOR UPDATE` row locks inside a transaction. No exception |
| **Every write = audit log** | `audit_logs` gets an INSERT for every mutation. No exceptions. Written as background task |
| **E-Undiyal ≠ Booking** | Completely separate tables, routes, services, and flow. Never mixed |
| **Frontend is never trusted** | Price, capacity, conflict bypass from client request body is always ignored |
| **Admin 2FA is mandatory** | No admin access without TOTP second factor |

---

## 2. Complete Folder Structure

```
smvd-backend/
├── app/
│   ├── main.py                        # FastAPI app init, middleware, router registration
│   ├── config.py                      # Pydantic BaseSettings (all env vars)
│   ├── database.py                    # Supabase asyncpg connection pool setup
│   │
│   ├── routers/
│   │   ├── public/
│   │   │   ├── services.py            # GET /api/v1/services
│   │   │   ├── availability.py        # GET /api/v1/availability
│   │   │   └── notices.py             # GET /api/v1/notices
│   │   ├── auth/
│   │   │   ├── otp.py                 # POST /api/v1/auth/otp/send, /verify
│   │   │   └── login.py               # POST /api/v1/auth/login, /admin/login, /admin/verify-2fa
│   │   ├── bookings/
│   │   │   ├── create.py              # POST /api/v1/bookings
│   │   │   ├── status.py              # GET /api/v1/bookings/{id}
│   │   │   └── list.py                # GET /api/v1/bookings (user's own)
│   │   ├── payments/
│   │   │   ├── orders.py              # POST /api/v1/payments/create-order
│   │   │   └── webhooks.py            # POST /api/v1/webhooks/payment/razorpay
│   │   ├── e_undiyal/
│   │   │   ├── donate.py              # POST /api/v1/e-undiyal/initiate
│   │   │   └── certificate.py         # POST /api/v1/e-undiyal/{id}/certificate-preference
│   │   └── admin/
│   │       ├── services.py            # /admin/services/*
│   │       ├── bookings.py            # /admin/bookings/*
│   │       ├── users.py               # /admin/users/*
│   │       ├── calendar.py            # /admin/calendar/*
│   │       ├── inventory.py           # /admin/inventory/*
│   │       ├── notices.py             # /admin/notices/*
│   │       ├── conflict_rules.py      # /admin/conflict-rules/*
│   │       ├── certificates.py        # /admin/certificates/*
│   │       └── reports.py             # /admin/reports/*
│   │
│   ├── services/
│   │   ├── booking_engine.py          # Core booking orchestration (10-step transaction)
│   │   ├── conflict_checker.py        # Kaapu/Kavasam, Chariot, Thirukalyanam rules
│   │   ├── calendar_service.py        # Date blocking/partial logic
│   │   ├── slot_service.py            # SELECT FOR UPDATE slot management
│   │   ├── payment_service.py         # Razorpay API wrapper
│   │   ├── webhook_service.py         # Webhook HMAC verification + processing
│   │   ├── e_undiyal_service.py       # Donation flow (independent)
│   │   ├── certificate_service.py     # 80G tax certificate workflow
│   │   ├── receipt_service.py         # PDF generation (WeasyPrint)
│   │   ├── notification_service.py    # SMS (MSG91) + Email (Resend)
│   │   ├── audit_service.py           # Immutable audit log writes
│   │   ├── report_service.py          # Report data aggregation
│   │   └── notice_service.py          # Notice publish/expire logic
│   │
│   ├── repositories/
│   │   ├── user_repo.py
│   │   ├── service_repo.py
│   │   ├── booking_repo.py
│   │   ├── payment_repo.py
│   │   ├── slot_repo.py               # All slot_inventory reads/writes
│   │   ├── conflict_repo.py
│   │   ├── calendar_repo.py
│   │   ├── notice_repo.py
│   │   ├── e_undiyal_repo.py
│   │   ├── certificate_repo.py
│   │   └── audit_repo.py              # INSERT only — no UPDATE/DELETE
│   │
│   ├── models/
│   │   ├── db/                        # SQLModel ORM table models
│   │   │   ├── user.py
│   │   │   ├── booking.py
│   │   │   ├── payment.py
│   │   │   ├── service.py
│   │   │   ├── slot.py
│   │   │   ├── notice.py
│   │   │   ├── e_undiyal.py
│   │   │   └── audit_log.py
│   │   └── schemas/                   # Pydantic request/response models
│   │       ├── auth.py
│   │       ├── booking.py
│   │       ├── payment.py
│   │       ├── service.py
│   │       ├── e_undiyal.py
│   │       ├── certificate.py
│   │       ├── notice.py
│   │       ├── report.py
│   │       └── admin.py
│   │
│   ├── dependencies/
│   │   ├── auth.py                    # JWT verify + role guard factory
│   │   └── db.py                      # DB session/connection injection
│   │
│   ├── middleware/
│   │   ├── rate_limit.py              # slowapi per-IP/per-user limits
│   │   ├── request_logging.py         # Structured JSON request logging
│   │   └── cors.py                    # CORS allowlist config
│   │
│   └── background/
│       ├── slot_cleanup.py            # Cancel expired pending_payment bookings
│       ├── notice_scheduler.py        # Auto publish/expire notices
│       └── report_generator.py        # Async large report generation
│
├── migrations/                        # Alembic migration files
│   ├── env.py
│   └── versions/
│       ├── 001_create_users.py
│       ├── 002_create_services.py
│       ├── 003_create_slot_inventory.py
│       ├── 004_create_bookings.py
│       ├── 005_create_payments.py
│       ├── 006_create_e_undiyal.py
│       ├── 007_create_conflict_rules.py
│       ├── 008_create_calendar_dates.py
│       ├── 009_create_notices.py
│       ├── 010_create_audit_logs.py
│       └── 011_seed_services_conflict_rules.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_booking_engine.py
│   │   ├── test_conflict_checker.py
│   │   ├── test_chariot_rules.py
│   │   ├── test_moolavar_abishegam.py
│   │   ├── test_annadhanam.py
│   │   ├── test_ganapathy_homam.py
│   │   ├── test_e_undiyal.py
│   │   ├── test_payment_webhooks.py
│   │   ├── test_calendar.py
│   │   └── test_admin_rbac.py
│   └── integration/
│       ├── test_booking_full_flow.py
│       ├── test_payment_full_flow.py
│       ├── test_capacity_concurrency.py
│       └── test_e_undiyal_flow.py
│
├── .env.example
├── .gitignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 3. Request-to-Response Workflow

### 3.1 Public Request — Check Availability

```
Client
  │  HTTPS GET /api/v1/availability?service_id=<uuid>&date=2026-08-01
  ▼
Cloudflare  →  Nginx  →  FastAPI Middleware Stack
                            ├── CORS check
                            ├── Rate limit check (100 req/min per IP)
                            └── Request logging
  ▼
availability.py router
  ├── Pydantic: validate service_id (UUID), date (valid date format)
  ├── calendar_service.check_date(date, service_id)
  │     → Query calendar_dates WHERE date = ?
  │     → status=blocked → return { available: false, reason: "BLOCKED" }
  │     → status=partial → check if service_id in allowed_service_ids
  │     → status=open (or no row) → continue
  ├── slot_service.get_availability(service_id, date, session)
  │     → SELECT from slot_inventory (read only, no lock)
  │     → capacity_remaining = total_capacity - confirmed_count - pending_count
  └── Return { available: bool, capacity_remaining: int, special_instructions: str }
  ▼
Background Task: audit_service.write_log("availability.checked")
  ▼
Response → Nginx → Cloudflare → Client
```

### 3.2 Booking Creation — Full 10-Step Transaction

```
Authenticated Devotee
  │  POST /api/v1/bookings
  │  Authorization: Bearer <JWT>
  │  Body: { service_id, date, session, num_persons, persons:[{name, star}] }
  ▼
Middleware:
  ├── JWT verify against Supabase JWKS
  ├── Extract app_role = "devotee"
  └── Rate limit: 10 bookings/user/hour
  ▼
booking/create.py router
  ▼
booking_engine.create_booking(user_id, request) — ALL STEPS IN ONE TRANSACTION
  │
  ├── Step 1: Pydantic Schema Validation
  │     ├── service_id → UUID
  │     ├── date → valid DATE, not in past
  │     ├── num_persons → int, 1 ≤ n ≤ 5
  │     └── persons[] → each has name (str) + star (str)
  │
  ├── Step 2: Calendar Check
  │     → calendar_service.check_date(date, service_id)
  │     → BLOCKED → HTTP 409 "Date not available"
  │
  ├── Step 3: Service Validation
  │     → service_repo.get_service(service_id)
  │     → is_active = false → HTTP 404
  │     → today + advance_booking_days > requested_date → HTTP 422
  │
  ├── Step 4: Conflict Rule Check
  │     → conflict_checker.check(service_id, date, session)
  │     → Kaapu booked + Kavasam request → HTTP 409 "Conflict"
  │     → Chariot already booked this session → HTTP 409
  │     → Thirukalyanam + morning chariot → HTTP 409
  │     → Ganapathy Homam + Chariot → set requires_approval=true, add notice
  │
  ├── Step 5: Slot Acquisition — BEGIN TRANSACTION
  │     → SELECT * FROM slot_inventory WHERE service_id=? AND date=? FOR UPDATE
  │     → confirmed + pending >= total_capacity → ROLLBACK → HTTP 409 "Slot full"
  │     → UPDATE slot_inventory SET pending_count = pending_count + 1
  │
  ├── Step 6: Duplicate Check
  │     → SELECT from bookings WHERE user_id=? AND service_id=? AND date=? AND session=?
  │       AND status IN ('confirmed','pending_payment')
  │     → Found → HTTP 409 "Already booked"
  │
  ├── Step 7: Special Service Rules
  │     → Moolavar Abishegam: num_families ≤ 10, persons_per_family ≤ 3
  │     → Annadhanam Meals: num_persons must == 1
  │
  ├── Step 8: Create Booking Records
  │     → INSERT into bookings (status=pending_payment, requires_approval=?)
  │     → INSERT into booking_persons (each person)
  │
  ├── Step 9: Create Payment Order
  │     → payment_service.create_order(booking_id, amount_paise)
  │     → POST to Razorpay API
  │     → INSERT into payments (status=initiated, gateway_order_id=?)
  │
  └── Step 10: COMMIT TRANSACTION
  │
  ▼
Background Task: audit_service.write_log("booking.created", ...)
  ▼
Response: { booking_id, booking_reference, gateway_order_id, amount_paise, requires_approval, notice? }
```

### 3.3 Payment Webhook Processing

```
Razorpay
  │  POST /api/v1/webhooks/payment/razorpay
  │  X-Razorpay-Signature: <hmac>
  ▼
webhook_service.verify_signature(raw_body, signature)
  → HMAC-SHA256 mismatch → HTTP 400 + security log + STOP
  ▼
Parse event type:
  ├── payment.captured → success_flow()
  └── payment.failed   → failure_flow()
  ▼
BEGIN TRANSACTION (success flow)
  ├── SELECT * FROM bookings WHERE id=? FOR UPDATE
  ├── Check status = pending_payment (idempotency — skip if already confirmed)
  ├── Verify amount matches expected amount_paise
  ├── SELECT * FROM slot_inventory WHERE ... FOR UPDATE (final capacity check)
  ├── If over capacity → initiate refund → reject booking
  ├── UPDATE bookings SET status = confirmed | pending_approval
  ├── UPDATE slot_inventory SET confirmed_count+=1, pending_count-=1
  └── UPDATE payments SET status=success, gateway_payment_id=?
COMMIT
  ▼
Background Tasks:
  ├── receipt_service.generate_pdf(booking_id) → Supabase Storage
  ├── notification_service.send_sms(phone, "Booking confirmed: SMV-...")
  ├── notification_service.send_email(email, ...)
  └── audit_service.write_log("payment.success", ...)
  ▼
HTTP 200 OK to Razorpay (must respond < 5 seconds)
```

---

## 4. Module Interactions

```
ROUTERS (HTTP Layer)
  └─calls─▶  SERVICES (Business Logic)
               ├─ booking_engine ──▶ conflict_checker
               │                ──▶ calendar_service
               │                ──▶ slot_service
               │                ──▶ payment_service
               │                ──▶ audit_service (background)
               │
               ├─ e_undiyal_service ──▶ payment_service
               │                   ──▶ certificate_service (after payment)
               │
               ├─ certificate_service ──▶ receipt_service
               │                     ──▶ notification_service
               │
               ├─ webhook_service ──▶ slot_service
               │                 ──▶ booking_engine (confirm step)
               │                 ──▶ audit_service (background)
               │
               └─ report_service (READ ONLY — never writes business data)

  └─calls─▶  REPOSITORIES (SQL Layer)
               booking_repo  slot_repo  payment_repo
               service_repo  user_repo  conflict_repo
               calendar_repo notice_repo e_undiyal_repo
               certificate_repo  audit_repo (INSERT ONLY)

  └─talks─▶  Supabase PostgreSQL (via asyncpg, PgBouncer port 6543)
```

### Critical Interaction Rules

| Rule | Reason |
|------|--------|
| Routers call Services only — never Repos directly | Keeps HTTP layer clean |
| Services call Repos for all DB operations | Single responsibility |
| audit_service is ALWAYS a BackgroundTask | Never blocks response |
| slot_service ALWAYS uses FOR UPDATE on writes | Zero overbooking |
| conflict_checker reads from DB at runtime | Rules configurable without code changes |
| E-Undiyal service never touches bookings/slot_inventory | Clean separation |

---

## 5. Database Flow

### 5.1 Booking Write Transaction

```
BEGIN TRANSACTION
│
├─ READ  services           → price, advance_days, conflict_group, active status
├─ READ  calendar_dates     → date open/blocked/partial
├─ READ  conflict_rules     → active rules for this service
├─ READ  bookings           → duplicate check for this user+service+date+session
│
├─ LOCK  slot_inventory     → SELECT FOR UPDATE (prevents race condition)
├─ CHECK confirmed_count + pending_count < total_capacity
│
├─ WRITE slot_inventory     → pending_count += 1
├─ WRITE bookings           → INSERT (status: pending_payment)
├─ WRITE booking_persons    → INSERT each person
├─ WRITE payments           → INSERT (status: initiated)
│
COMMIT
│
└─ BACKGROUND: WRITE audit_logs → INSERT (never UPDATE/DELETE)
```

### 5.2 Table Write Ownership

| Table | Who Writes | Who Reads |
|-------|-----------|-----------|
| `users` | Supabase Auth + FastAPI profile | Auth deps, admin API |
| `services` | Admin API only | All services, public API |
| `slot_inventory` | slot_service (FOR UPDATE) | availability router, admin |
| `bookings` | booking_engine, webhook, admin | user list, admin |
| `booking_persons` | booking_engine | admin detail view |
| `payments` | payment_service, webhook | admin, receipt |
| `e_undiyal_transactions` | e_undiyal_service, webhook | admin, certificate |
| `conflict_rules` | Admin API only | conflict_checker (runtime) |
| `calendar_dates` | Admin API only | calendar_service |
| `notices` | Admin API only | public notices API |
| `audit_logs` | audit_service ONLY — INSERT ONLY | Admin reports |

### 5.3 PostgreSQL-Level Constraints

- `audit_logs`: GRANT INSERT only — no UPDATE/DELETE even by service role
- `bookings.booking_reference`: UNIQUE
- `e_undiyal_transactions.transaction_reference`: UNIQUE
- `payments.gateway_order_id`: UNIQUE (idempotency)
- `calendar_dates.date`: UNIQUE
- All enum columns: CHECK constraints

---

## 6. Authentication & Authorization Flow

### 6.1 Devotee — Phone OTP

```
POST /api/v1/auth/otp/send  { phone: "+91XXXXXXXXXX" }
  → Validate E.164 format
  → Supabase Auth signInWithOtp({ phone })
  → OTP sent via MSG91/Twilio
  → Response: { message: "OTP sent" }

POST /api/v1/auth/otp/verify  { phone, otp }
  → Supabase Auth verifyOtp({ phone, token, type:"sms" })
  → Returns { access_token, refresh_token, user }
  → FastAPI: INSERT into users if new user (role: "devotee")
  → Response: { access_token, refresh_token, profile }
```

### 6.2 Admin — Email + TOTP 2FA

```
POST /api/v1/auth/admin/login  { email, password }
  → Supabase Auth signInWithPassword
  → Extract app_role from JWT claims
  → If role NOT IN [admin, super_admin] → HTTP 403
  → Return: { session_token (short-lived, pre-2FA) }

POST /api/v1/auth/admin/verify-2fa  { session_token, totp_code }
  → Verify TOTP (Google Authenticator compatible)
  → If valid → return full admin JWT (4hr expiry)
  → If invalid → HTTP 401
```

### 6.3 JWT Verification (Every Protected Request)

```
Authorization: Bearer <token>
  ↓
dependencies/auth.py — require_role("devotee" | "staff" | "admin" | "super_admin")
  1. Extract Bearer token from Authorization header
  2. Fetch Supabase JWKS (cached for 1 hour)
  3. Decode + verify JWT signature
  4. Check token expiry (exp claim)
  5. Extract app_role claim
  6. Check role hierarchy: super_admin > admin > staff > devotee
  7. If insufficient role → HTTP 403
  8. Return CurrentUser(id, role)
```

### 6.4 Role Matrix

| Action | devotee | staff | admin | super_admin |
|--------|---------|-------|-------|-------------|
| Create booking | ✅ | ❌ | ❌ | ✅ |
| View own bookings | ✅ | ❌ | ✅ | ✅ |
| E-Undiyal donation | ✅ | ❌ | ❌ | ✅ |
| View all bookings | ❌ | ✅ | ✅ | ✅ |
| Approve/reject booking | ❌ | ❌ | ✅ | ✅ |
| Manage calendar | ❌ | ❌ | ✅ | ✅ |
| Manage notices | ❌ | ❌ | ✅ | ✅ |
| Manage services | ❌ | ❌ | ❌ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ✅ |
| Manage conflict rules | ❌ | ❌ | ❌ | ✅ |
| View reports | ❌ | ✅ | ✅ | ✅ |
| Export data | ❌ | ❌ | ✅ | ✅ |
| Issue 80G certificate | ❌ | ❌ | ✅ | ✅ |

---

## 7. Service Layer Responsibilities

### booking_engine.py
**Owns the entire booking creation transaction.**
- Orchestrates all 10 steps in a single DB transaction
- Calls: calendar_service → service_repo → conflict_checker → slot_service → booking_repo → payment_service
- Returns: `BookingResult(booking_id, reference, payment_order_id, requires_approval, notice)`
- If ANY step fails → full rollback, no partial state

### conflict_checker.py
**Data-driven conflict rule enforcement (reads DB at runtime).**
- `check_conflicts(service_id, date, session)` → queries `conflict_rules` table
- Enforces: Kaapu/Kavasam mutual exclusivity (bidirectional)
- Enforces: Chariot one-per-session (uses slot_inventory capacity=1)
- Enforces: Thirukalyanam blocks morning chariot (`a_blocks_b` direction)
- Flags: Ganapathy Homam + Chariot → `requires_approval=True`, includes notice text
- Returns: `ConflictResult(blocked: bool, requires_approval: bool, notice: str | None)`

### slot_service.py
**All slot capacity operations go through here.**
- `acquire_slot(service_id, date, session, db_conn)` → FOR UPDATE, increment pending
- `release_slot(slot_id, db_conn)` → decrement pending (timeout/failure cleanup)
- `confirm_slot(slot_id, db_conn)` → confirmed+1, pending-1 (payment success)
- `block_slot(service_id, date, session)` → admin action
- **Never called outside a database transaction**

### calendar_service.py
**Date availability logic.**
- `check_date(date, service_id)` → query `calendar_dates` → `DateStatus`
- Default (no row): OPEN
- BLOCKED: return 409
- PARTIAL: check if service_id in `allowed_service_ids`
- Used at the START of every booking attempt, before any slot lock

### payment_service.py
**Razorpay API abstraction layer.**
- `create_order(amount_paise, currency, booking_id)` → Razorpay API → `gateway_order_id`
- `initiate_refund(payment_id, amount_paise)` → Razorpay refund API → `refund_id`
- All API keys from environment variables only — never hardcoded

### webhook_service.py
**Handles inbound payment gateway callbacks.**
- `verify_signature(raw_body, sig_header)` → HMAC-SHA256 verify → HTTP 400 on failure
- `process_success(event_data)` → confirm slot + update booking + update payment
- **Idempotent**: if booking already `confirmed` → skip silently (gateway retries safe)

### e_undiyal_service.py
**Donation flow — completely independent from bookings.**
- `initiate_donation(donor_data, amount)` → create e_undiyal_transaction + payment order
- `complete_donation(transaction_id)` → update status + trigger 80G workflow
- Never touches: `bookings`, `slot_inventory`, `conflict_rules`, `booking_persons`

### certificate_service.py
**80G tax exemption certificate workflow.**
- `trigger_80g_workflow(transaction_id)` → set `certificate_status=pending_details`
- `process_preference(transaction_id, preference)` → route to in_person or courier flow
- `issue_certificate(transaction_id, cert_data)` → generate PDF → Supabase Storage → notify
- `mark_dispatched(transaction_id, courier_data)` → update tracking info → notify

### audit_service.py
**Immutable audit trail.**
- `write_log(action, entity_type, entity_id, actor_id, before, after, ip, user_agent)` → INSERT
- **Always called as FastAPI BackgroundTask** — never blocks the response
- Uses separate DB connection — commits independently from main transaction

### notification_service.py
**Outbound SMS and Email.**
- `send_sms(phone, message)` → MSG91/Twilio
- `send_email(to, subject, html_body)` → Resend
- Fire-and-forget in BackgroundTask — failures logged, never bubble up to user

### receipt_service.py
**PDF generation for booking receipts and 80G certificates.**
- `generate_booking_receipt(booking_id)` → WeasyPrint HTML→PDF → Supabase Storage → signed URL
- `generate_donation_receipt(transaction_id)` → WeasyPrint → Supabase Storage
- `generate_certificate_pdf(transaction_id, cert_data)` → PDF with temple 80G number

### report_service.py
**Analytics and reporting — READ ONLY, never writes business data.**
- `get_daily_summary(date)` → aggregated metrics
- `get_revenue_report(start, end)` → revenue breakdown
- `get_occupancy_report(service_id, month)` → utilization percentages
- For large reports: create background job → upload to Supabase Storage → return signed URL

---

## 8. Repository Layer Responsibilities

Repositories are **thin SQL-only layers**. No business logic. Parameterized queries only.

### booking_repo.py
- `create_booking(data)` → INSERT into bookings, return booking record
- `insert_persons(booking_id, persons)` → INSERT into booking_persons (bulk)
- `get_booking(booking_id)` → SELECT with JOIN to booking_persons
- `get_user_bookings(user_id, page, limit)` → paginated SELECT
- `check_duplicate(user_id, service_id, date, session)` → COUNT check
- `update_status(booking_id, new_status)` → UPDATE bookings
- `get_all_bookings(filters)` → Admin: SELECT with dynamic WHERE filters
- `get_pending_approvals()` → SELECT WHERE status=pending_approval

### slot_repo.py
- `get_slot_for_update(service_id, date, session, conn)` → **SELECT FOR UPDATE** (must be in transaction)
- `get_or_create_slot(service_id, date, session)` → UPSERT with defaults
- `increment_pending(slot_id, conn)` → UPDATE pending_count += 1
- `decrement_pending(slot_id, conn)` → UPDATE pending_count -= 1
- `confirm_slot(slot_id, conn)` → UPDATE confirmed_count+=1, pending_count-=1
- `block_slot(slot_id, reason)` → UPDATE is_blocked=true

### audit_repo.py
- **INSERT ONLY** — no read, no update, no delete
- `insert_log(log_data)` → direct asyncpg execute (not ORM, for speed)
- Uses service role that has INSERT GRANT only on audit_logs

### All Other Repos
- Standard parameterized SELECT/INSERT/UPDATE
- Return typed domain objects, not raw DB rows
- All queries use `$1, $2` placeholders (asyncpg style) — never f-strings in SQL

---

## 9. Validation Strategy

### Layer 1 — Pydantic Schema (First, before any code runs)

| Field | Validation Rule |
|-------|----------------|
| `service_id` | UUID format |
| `date` | Valid date format, ≥ today |
| `num_persons` | Integer, 1 ≤ n ≤ 5 |
| `phone` | E.164 regex (`^\+[1-9]\d{1,14}$`) |
| `amount_paise` | Positive integer |
| `pan_number` | 10-char `[A-Z]{5}[0-9]{4}[A-Z]` |
| `email` | Email format (Pydantic EmailStr) |
| `persons` array | Min 1 item, each has `name` (str, max 100) + `star` (str, max 50) |
| `donor_location_type` | Enum: `local`, `domestic`, `international` |

### Layer 2 — Business Rule Validation (Service layer, after schema pass)

| Rule | Service Responsible |
|------|-------------------|
| Date ≥ today + advance_booking_days | booking_engine |
| Service is_active = true | booking_engine |
| Date is open or service allowed | calendar_service |
| No conflicting booking on same date | conflict_checker |
| Slot has remaining capacity | slot_service |
| No duplicate booking (same user+service+date+session) | booking_repo |
| Moolavar Abishegam: ≤10 families, ≤3 persons/family | booking_engine |
| Annadhanam Meals: exactly 1 person | booking_engine |
| Annadhanam Prasadha Thonnai: no duplicate session | booking_repo |
| Ganapathy Homam: 5-day advance | booking_engine |
| Payment amount matches booking amount | webhook_service |

### Layer 3 — Database Constraints (Final defense)

- UNIQUE on reference numbers, gateway_order_id
- NOT NULL on required columns
- CHECK constraints on status enums
- RLS blocks unauthorized access even at DB level

---

## 10. Error Handling Strategy

### HTTP Status Code Map

| Situation | Code | Response |
|-----------|------|----------|
| Schema validation failure | 422 | `{ detail: [{loc, msg, type}] }` |
| Auth failure (bad/expired token) | 401 | `{ detail: "Invalid or expired token" }` |
| Insufficient role | 403 | `{ detail: "Insufficient permissions" }` |
| Resource not found | 404 | `{ detail: "Booking not found" }` |
| Slot full | 409 | `{ detail: "...", code: "SLOT_FULL" }` |
| Duplicate booking | 409 | `{ detail: "...", code: "DUPLICATE_BOOKING" }` |
| Date blocked | 409 | `{ detail: "...", code: "DATE_BLOCKED" }` |
| Conflict rule triggered | 409 | `{ detail: "...", code: "CONFLICT_RULE" }` |
| Advance days violation | 422 | `{ detail: "...", code: "ADVANCE_DAYS" }` |
| Payment signature invalid | 400 | `{ detail: "Invalid payment signature" }` |
| Server error | 500 | `{ detail: "Internal server error" }` (no trace) |

### Standard Error Response Body

```json
{
  "detail": "Human readable message",
  "code": "MACHINE_READABLE_CODE",
  "field": "field_name_if_applicable"
}
```

### Global Exception Handler (registered in main.py)

1. Log full stack trace to application logger (NOT returned to client)
2. Return sanitized HTTP 500 to client
3. Trigger Sentry alert if in production
4. Write to audit_log with severity=ERROR

---

## 11. Logging Strategy

### Log Levels

| Level | When |
|-------|------|
| DEBUG | SQL queries, FOR UPDATE acquisitions (dev only, disabled in prod) |
| INFO | Request received, booking created, payment confirmed, job completed |
| WARNING | Duplicate webhook, rate limit hit, slot near capacity, webhook retry |
| ERROR | DB connection failure, payment gateway unreachable, job failure |
| CRITICAL | HMAC signature mismatch (security event), RLS violation detected |

### Structured Log Format (JSON, every entry)

```json
{
  "timestamp": "2026-08-01T10:30:00.000Z",
  "level": "INFO",
  "request_id": "<uuid-per-request>",
  "user_id": "<uuid-or-null>",
  "user_role": "devotee",
  "method": "POST",
  "path": "/api/v1/bookings",
  "status_code": 201,
  "duration_ms": 234,
  "ip": "1.2.3.4",
  "message": "Booking created",
  "booking_id": "<uuid>",
  "service_id": "<uuid>"
}
```

### Never Log

- JWT access tokens or refresh tokens
- Payment card numbers
- PAN numbers in plaintext
- Passwords or TOTP codes
- Supabase service role key

---

## 12. Background Jobs

### APScheduler Jobs (startup, registered in main.py)

| Job | Schedule | Description |
|-----|----------|-------------|
| `slot_cleanup` | Every 5 min | Cancel `pending_payment` bookings > 15 min old → release slot |
| `notice_scheduler` | Every 5 min | Activate/expire notices by `published_at`/`expires_at` |
| `metrics_snapshot` | Daily 00:05 IST | Write daily KPI snapshot to `metrics_snapshots` |
| `report_cleanup` | Sunday 02:00 IST | Delete expired PDFs from Supabase Storage |

### Per-Request Background Tasks (FastAPI BackgroundTasks)

These run after the HTTP response is sent — client does not wait for them:

| Trigger | Background Task |
|---------|----------------|
| Any write operation | `audit_service.write_log(...)` |
| Payment confirmed | `receipt_service.generate_pdf(booking_id)` |
| Payment confirmed | `notification_service.send_sms(phone, ...)` |
| E-Undiyal payment confirmed | `certificate_service.trigger_80g_workflow(transaction_id)` |
| Certificate ready | `notification_service.send_email(donor_email, ...)` |

---

## 13. Deployment Flow

### GitHub Actions CI/CD Pipeline

```
Push to feature branch
  ↓
[1] pytest unit tests
[2] Bandit security scan
[3] detect-secrets scan (no creds in code)
[4] Build Docker image
  ↓ (merge to staging)
[5] Alembic migration on staging DB
[6] Deploy to Railway staging
[7] Health check: GET /api/v1/health → 200
[8] Notify team
  ↓ (merge to main — manual approval required)
[9]  Alembic migration on production DB
[10] Railway rolling deploy to production
[11] Health check
[12] Tag release with git commit SHA
```

### Environments

| Environment | Git Branch | Supabase Project | Railway Service |
|-------------|-----------|-----------------|-----------------|
| Local Dev | `feature/*` | `smvd-dev` | localhost:8000 |
| Staging | `staging` | `smvd-staging` | staging.api.smvd.in |
| Production | `main` | `smvd-prod` | api.smvd.in |

---

## 14. Production Readiness Requirements

### Security Checklist

- [ ] All env vars in Railway — none in codebase
- [ ] RLS enabled on all Supabase tables
- [ ] `audit_logs` INSERT-only grant verified at PostgreSQL level
- [ ] Admin TOTP 2FA working end-to-end
- [ ] Rate limiting on OTP (3/10min), login (5/5min), bookings (10/hr)
- [ ] CORS allowlist: production domains only, no wildcards
- [ ] HTTPS enforced — HTTP redirects to HTTPS
- [ ] Razorpay webhook HMAC verified on every call
- [ ] No internal stack traces in error responses

### Business Rules Verification

- [ ] All 10 services in DB with correct `advance_booking_days`
- [ ] Moolavar Abishegam `slot_inventory` configured (total_capacity=10 for families)
- [ ] All `conflict_rules` rows seeded (Kaapu/Kavasam, Chariot, Thirukalyanam)
- [ ] Kaapu+Kavasam mutual exclusivity tested with live API
- [ ] Chariot: one per session verified with concurrent requests
- [ ] Ganapathy Homam 5-day advance verified
- [ ] Annadhanam duplicate booking prevention verified
- [ ] E-Undiyal routes completely isolated from booking routes
- [ ] 80G certificate flow end-to-end tested (local + domestic + international)

### Performance

- [ ] Concurrent load test: 50 simultaneous bookings for capacity=5 → exactly 5 confirmed
- [ ] Zero overbooking verified
- [ ] p95 API latency < 300ms under normal load
- [ ] `slot_cleanup` background job verified active

### Operations

- [ ] `GET /api/v1/health` returns `{ status: "ok", db: "connected" }`
- [ ] Sentry error tracking configured and tested
- [ ] UptimeRobot monitoring active (5min check interval)
- [ ] Railway logs accessible and readable
- [ ] Razorpay KYC complete, webhook URL registered in Razorpay dashboard
- [ ] Rollback tested with previous Railway deployment
- [ ] Supabase Pro backup verified (daily backup shown in dashboard)

---

## 15. Module Ownership Map

| Module | Owner | Reviewer |
|--------|-------|---------|
| Project setup, config, main.py, middleware | **Abhinav** | Athreyan |
| Database connection, migrations | **Abhinav** | Athreyan |
| Auth (OTP, login, JWT, TOTP 2FA) | **Abhinav** | Athreyan |
| Booking engine + conflict checker | **Abhinav** | Athreyan |
| Slot service + slot_inventory | **Abhinav** | Athreyan |
| Payment service + webhook handler | **Abhinav** | Athreyan |
| Calendar management system | **Abhinav** | Athreyan |
| Background jobs (slot cleanup, notice scheduler) | **Abhinav** | Athreyan |
| Services catalogue (DB models + admin API) | **Athreyan** | Abhinav |
| E-Undiyal donation flow | **Athreyan** | Abhinav |
| 80G Certificate workflow | **Athreyan** | Abhinav |
| Notice management system | **Athreyan** | Abhinav |
| CMS admin APIs (bookings, users, services, calendar) | **Athreyan** | Abhinav |
| Reporting + analytics + KPI dashboard | **Athreyan** | Abhinav |
| User management admin API | **Athreyan** | Abhinav |
| CI/CD pipeline + Dockerfile | **Abhinav** | Athreyan |
| Staging + production deployment | **Abhinav** | Athreyan |

---

## 16. 14-Day Milestone Overview

| Day | Abhinav | Athreyan | End-of-Day Gate |
|-----|---------|----------|-----------------|
| 1 | Project setup, config, DB, health check | All DB migrations (11 files) | `GET /health` returns 200, all tables exist in Supabase Dev |
| 2 | Auth: OTP, email/password, JWT deps | Services catalogue + schemas | Auth endpoints working, services list API live |
| 3 | Booking engine Steps 1–7 | Slot inventory management | Booking creation works (pre-payment) |
| 4 | Conflict rules engine (all 4 rules) | E-Undiyal donation flow | All conflict rules enforced, E-Undiyal initiation works |
| 5 | Payment service + Razorpay order creation | 80G certificate workflow | Payment order created successfully |
| 6 | Webhook handler + booking confirmation | Notice management system | Full payment→booking confirmed flow works |
| 7 | Calendar management system | Admin booking management API | Calendar blocking works, admin booking APIs live |
| 8 | Background jobs (slot cleanup, notice) | Admin user management + RBAC guards | Background jobs running |
| 9 | Unit tests: auth, booking, conflicts | Admin reports: daily/weekly | Core unit tests all passing |
| 10 | Unit tests: payment, webhook, concurrency | Admin services + calendar + KPIs | Full unit test suite passing |
| 11 | Integration: booking + payment full flow | Integration: E-Undiyal + certificate | Integration tests passing |
| 12 | Security hardening + rate limiting | RBAC full test + admin audit | Security controls verified |
| 13 | Staging deploy + CI/CD pipeline | Final bug fixes + staging UAT | Staging environment live and tested |
| 14 | Load test + production deploy | Production checklist + monitoring | **PRODUCTION LIVE** |

---

*This master plan is the single source of truth for execution.*  
*All decisions must align with `backend_architecture.md`.*  
*Daily sync: 15 minutes, 9:00 AM. Decisions logged in GitHub PR comments.*
