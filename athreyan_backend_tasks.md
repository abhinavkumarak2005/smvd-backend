# Sri Manakula Vinayagar Devasthanam — Athreyan Backend Tasks

**Developer:** Athreyan  
**Role:** Backend Developer  
**Period:** Day 1 – Day 14  
**Modules Owned:** DB Migrations · Services Catalogue · E-Undiyal · 80G Certificate · Notice Management · CMS Admin APIs · Reporting · User Management

> Read `backend_master_plan.md` fully before starting Day 1.  
> Coordinate with Abhinav daily at 9:00 AM.  
> Your migrations (Day 1) are a blocker for Abhinav's Day 3 work — prioritize them.

---

## Day 1 — All Database Migrations

**Focus:** Create all 11 Alembic migration files. This is the highest priority task of the sprint.  
**Estimated Effort:** 8 hours  
**Why Critical:** Abhinav cannot implement the booking engine (Day 3) without these tables existing.

### Tasks

#### 1.1 Alembic Initialization (30 min)

Abhinav will set up `alembic.ini` and `migrations/env.py`. Your task is to write all migration version files. Coordinate: Abhinav does init, you write migrations.

#### 1.2 Migration 001 — users (45 min)

```
Table: users
Columns:
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  phone           TEXT UNIQUE
  email           TEXT UNIQUE
  full_name       TEXT
  role            TEXT DEFAULT 'devotee' CHECK (role IN ('devotee','staff','admin','super_admin'))
  is_active       BOOLEAN DEFAULT TRUE
  totp_secret     TEXT                      -- For admin 2FA (encrypted)
  totp_enabled    BOOLEAN DEFAULT FALSE
  created_at      TIMESTAMPTZ DEFAULT NOW()
  updated_at      TIMESTAMPTZ DEFAULT NOW()

Indexes: idx_users_phone, idx_users_email
```

#### 1.3 Migration 002 — services (45 min)

```
Table: services
Columns:
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid()
  name                 TEXT NOT NULL
  name_tamil           TEXT
  category             TEXT CHECK (category IN ('archanai','homam','seva','chariot','annadhanam','special'))
  description          TEXT
  description_tamil    TEXT
  price_paise          INTEGER NOT NULL               -- in paise (1 INR = 100 paise)
  max_persons          INTEGER DEFAULT 5
  advance_booking_days INTEGER DEFAULT 1
  session              TEXT CHECK (session IN ('morning','evening','both','na')) DEFAULT 'na'
  is_active            BOOLEAN DEFAULT TRUE
  image_url            TEXT
  sort_order           INTEGER DEFAULT 0
  created_at           TIMESTAMPTZ DEFAULT NOW()
  updated_at           TIMESTAMPTZ DEFAULT NOW()
```

#### 1.4 Migration 003 — slot_inventory (45 min)

```
Table: slot_inventory
Columns:
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  service_id      UUID NOT NULL REFERENCES services(id)
  date            DATE NOT NULL
  session         TEXT DEFAULT 'na'
  total_capacity  INTEGER NOT NULL
  confirmed_count INTEGER DEFAULT 0 CHECK (confirmed_count >= 0)
  pending_count   INTEGER DEFAULT 0 CHECK (pending_count >= 0)
  is_blocked      BOOLEAN DEFAULT FALSE
  block_reason    TEXT
  created_at      TIMESTAMPTZ DEFAULT NOW()
  updated_at      TIMESTAMPTZ DEFAULT NOW()

Unique constraint: (service_id, date, session)
Indexes: idx_slot_service_date, idx_slot_date
```

#### 1.5 Migration 004 — bookings (1 hour)

```
Table: bookings
Columns:
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid()
  booking_reference  TEXT UNIQUE NOT NULL    -- e.g. SMV-BK-20260801-001
  user_id            UUID NOT NULL REFERENCES users(id)
  service_id         UUID NOT NULL REFERENCES services(id)
  slot_id            UUID REFERENCES slot_inventory(id)
  booking_date       DATE NOT NULL
  session            TEXT DEFAULT 'na'
  num_persons        INTEGER DEFAULT 1
  amount_paise       INTEGER NOT NULL
  status             TEXT DEFAULT 'pending_payment' CHECK (status IN (
                       'pending_payment','confirmed','pending_approval',
                       'approved','rejected','cancelled','expired','payment_failed'))
  requires_approval  BOOLEAN DEFAULT FALSE
  approval_note      TEXT
  approved_by        UUID REFERENCES users(id)
  approved_at        TIMESTAMPTZ
  cancelled_at       TIMESTAMPTZ
  cancellation_note  TEXT
  special_note       TEXT                    -- Conflict notice text shown to user
  created_at         TIMESTAMPTZ DEFAULT NOW()
  updated_at         TIMESTAMPTZ DEFAULT NOW()

Table: booking_persons
Columns:
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
  booking_id  UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE
  full_name   TEXT NOT NULL
  star        TEXT NOT NULL
  created_at  TIMESTAMPTZ DEFAULT NOW()

Indexes: idx_bookings_user_id, idx_bookings_service_date, idx_bookings_status, idx_bookings_reference
```

#### 1.6 Migration 005 — payments (30 min)

```
Table: payments
Columns:
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid()
  booking_id          UUID REFERENCES bookings(id)
  e_undiyal_id        UUID                        -- for donation payments
  gateway_order_id    TEXT UNIQUE NOT NULL
  gateway_payment_id  TEXT
  gateway_refund_id   TEXT
  amount_paise        INTEGER NOT NULL
  currency            TEXT DEFAULT 'INR'
  status              TEXT DEFAULT 'initiated' CHECK (status IN (
                        'initiated','success','failed','refunded','expired'))
  payment_method      TEXT
  paid_at             TIMESTAMPTZ
  refunded_at         TIMESTAMPTZ
  created_at          TIMESTAMPTZ DEFAULT NOW()
  updated_at          TIMESTAMPTZ DEFAULT NOW()

Index: idx_payments_gateway_order_id, idx_payments_booking_id
```

#### 1.7 Migration 006 — e_undiyal_transactions (1 hour)

```
Table: e_undiyal_transactions
Columns:
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid()
  transaction_reference TEXT UNIQUE NOT NULL       -- e.g. SMV-EU-20260801-001
  user_id               UUID REFERENCES users(id)
  donor_name            TEXT NOT NULL
  donor_phone           TEXT
  donor_email           TEXT
  amount_paise          INTEGER NOT NULL
  donation_category     TEXT
  status                TEXT DEFAULT 'initiated' CHECK (status IN (
                          'initiated','success','failed','refunded'))
  -- 80G Certificate columns:
  tax_certificate_eligible   BOOLEAN DEFAULT TRUE
  certificate_status         TEXT DEFAULT 'pending_details' CHECK (certificate_status IN (
                               'pending_details','processing','ready','dispatched','delivered'))
  delivery_mode              TEXT CHECK (delivery_mode IN ('in_person','courier'))
  donor_location_type        TEXT CHECK (donor_location_type IN ('local','domestic','international'))
  donor_address              JSONB                -- { full_name, door_no, street, city, state, pincode, country, phone, pan_number }
  certificate_number         TEXT UNIQUE
  certificate_url            TEXT
  courier_tracking_id        TEXT
  courier_partner            TEXT
  dispatched_at              TIMESTAMPTZ
  details_submitted_at       TIMESTAMPTZ
  certificate_issued_by      UUID REFERENCES users(id)
  certificate_issued_at      TIMESTAMPTZ
  created_at                 TIMESTAMPTZ DEFAULT NOW()
  updated_at                 TIMESTAMPTZ DEFAULT NOW()

Indexes: idx_e_undiyal_user_id, idx_e_undiyal_status, idx_e_undiyal_cert_status
```

#### 1.8 Migration 007 — conflict_rules (30 min)

```
Table: conflict_rules
Columns:
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid()
  service_a_id   UUID NOT NULL REFERENCES services(id)
  service_b_id   UUID NOT NULL REFERENCES services(id)
  rule_type      TEXT NOT NULL CHECK (rule_type IN (
                   'mutual_exclusion','session_exclusive','a_blocks_b','requires_approval'))
  direction      TEXT DEFAULT 'bidirectional' CHECK (direction IN ('bidirectional','a_to_b'))
  notice_text    TEXT
  is_active      BOOLEAN DEFAULT TRUE
  created_at     TIMESTAMPTZ DEFAULT NOW()
```

#### 1.9 Migration 008 — calendar_dates (30 min)

```
Table: calendar_dates
Columns:
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid()
  date                DATE UNIQUE NOT NULL
  status              TEXT DEFAULT 'open' CHECK (status IN ('open','blocked','partial'))
  notes               TEXT
  notes_tamil         TEXT
  allowed_service_ids JSONB DEFAULT '[]'        -- Array of service UUIDs for partial status
  created_by          UUID REFERENCES users(id)
  created_at          TIMESTAMPTZ DEFAULT NOW()
  updated_at          TIMESTAMPTZ DEFAULT NOW()

Index: idx_calendar_date
```

#### 1.10 Migration 009 — notices (30 min)

```
Table: notices
Columns:
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
  title        TEXT NOT NULL
  title_tamil  TEXT
  body         TEXT NOT NULL
  body_tamil   TEXT
  category     TEXT CHECK (category IN ('general','booking','holiday','event','urgent')) DEFAULT 'general'
  priority     INTEGER DEFAULT 0
  status       TEXT DEFAULT 'draft' CHECK (status IN ('draft','scheduled','active','expired'))
  published_at TIMESTAMPTZ
  expires_at   TIMESTAMPTZ
  created_by   UUID REFERENCES users(id)
  created_at   TIMESTAMPTZ DEFAULT NOW()
  updated_at   TIMESTAMPTZ DEFAULT NOW()

Index: idx_notices_status, idx_notices_published_at
```

#### 1.11 Migration 010 — audit_logs (30 min)

```
Table: audit_logs
Columns:
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
  action       TEXT NOT NULL              -- e.g. 'booking.created', 'payment.success'
  entity_type  TEXT                       -- 'booking', 'payment', 'user', ...
  entity_id    UUID
  actor_id     UUID                       -- User who performed the action
  actor_role   TEXT
  before_state JSONB
  after_state  JSONB
  ip_address   TEXT
  user_agent   TEXT
  severity     TEXT DEFAULT 'info' CHECK (severity IN ('info','warning','error','critical'))
  created_at   TIMESTAMPTZ DEFAULT NOW()

Indexes: idx_audit_entity, idx_audit_actor, idx_audit_action, idx_audit_created_at

IMPORTANT: After migration, apply PostgreSQL grant:
  REVOKE UPDATE, DELETE ON audit_logs FROM service_role;
  -- Only INSERT allowed
```

#### 1.12 Migration 011 — Seed Data (1 hour)

Seed all 10 services with correct data from the architecture document:

```
Services to seed:
1.  Moolavar Abishegam         — category: archanai,  price_paise: TBD, advance_booking_days: 1, max_persons: 30 (10 families × 3)
2.  Ganapathy Homam            — category: homam,     price_paise: TBD, advance_booking_days: 5
3.  Kaapu (Sandhana Kaappu)   — category: seva,      price_paise: TBD, advance_booking_days: 1
4.  Kaapu (Vennai Kaappu)     — category: seva,      price_paise: TBD, advance_booking_days: 1
5.  Kavasam                    — category: seva,      price_paise: TBD, advance_booking_days: 1
6.  Gold Chariot               — category: chariot,   price_paise: TBD, advance_booking_days: 1, session: both
7.  Silver Chariot             — category: chariot,   price_paise: TBD, advance_booking_days: 1, session: both
8.  Urchavar Thirukalyanam     — category: special,   price_paise: TBD, advance_booking_days: 1, session: morning
9.  Annadhanam (Prasadha Thonnai) — category: annadhanam, price_paise: TBD
10. Annadhanam (Meals)         — category: annadhanam, price_paise: TBD, max_persons: 1

Conflict rules to seed (coordinate with Abhinav for service UUIDs):
- Kaapu_Sandhana ↔ Kavasam: mutual_exclusion
- Kaapu_Vennai ↔ Kavasam: mutual_exclusion
- Thirukalyanam → Gold_Chariot_morning: a_blocks_b
- Ganapathy_Homam + Gold_Chariot: requires_approval

Default slot_inventory for chariots (capacity=1 per session per date):
- Do NOT pre-create slots. Slots are created on first booking attempt (get_or_create_slot).
```

> **Get exact prices from the temple management before seeding.** Use placeholder values (1 INR = 100 paise) if prices are not yet confirmed.

---

### Day 1 Completion Criteria

- [ ] `alembic upgrade head` completes with zero errors
- [ ] All 11 tables exist in Supabase dev DB (verify in Supabase dashboard)
- [ ] `audit_logs` has only INSERT grant for service_role (verify with Supabase SQL editor)
- [ ] All 10 services seeded in `services` table
- [ ] Conflict rules seeded
- [ ] Notify Abhinav: "All migrations done, tables up, seed data in."

---

## Day 2 — Services Catalogue + Pydantic Schemas

**Focus:** Public services API, service schemas, admin service management schemas.  
**Estimated Effort:** 6 hours

### Tasks

#### 2.1 repositories/service_repo.py (1 hour)

```
get_all_services(active_only=True)
  → SELECT * FROM services WHERE is_active = ? ORDER BY sort_order

get_service(service_id)
  → SELECT * FROM services WHERE id = ?
  → Return None if not found

create_service(data)
  → INSERT INTO services (...) RETURNING *

update_service(service_id, data)
  → UPDATE services SET ... WHERE id = ?

toggle_active(service_id, is_active)
  → UPDATE services SET is_active = ? WHERE id = ?
```

#### 2.2 models/schemas/service.py (30 min)

```
ServiceResponse:
  id, name, name_tamil, category, description, description_tamil,
  price_paise, max_persons, advance_booking_days, session, is_active,
  image_url, sort_order

ServiceCreateRequest:
  name, name_tamil, category, description, price_paise, max_persons,
  advance_booking_days, session, image_url, sort_order

ServiceUpdateRequest (all optional fields):
  Same as create but all Optional
```

#### 2.3 routers/public/services.py (1 hour)

```
GET /api/v1/services
  → service_repo.get_all_services(active_only=True)
  → Return list of ServiceResponse

GET /api/v1/services/{service_id}
  → service_repo.get_service(service_id)
  → If None: 404
  → Return ServiceResponse
```

No auth required for public service endpoints.

#### 2.4 models/schemas/booking.py (1 hour)

Define all booking-related Pydantic models that Abhinav's routes need:

```
PersonRequest:
  full_name: str (min_length=2, max_length=100)
  star: str (min_length=2, max_length=50)

BookingCreateRequest:
  service_id: UUID
  booking_date: date
  session: Literal['morning','evening','na'] = 'na'
  num_persons: int (ge=1, le=5)
  persons: list[PersonRequest] (min_length=1, max_length=5)

BookingResponse:
  id: UUID
  booking_reference: str
  service_id: UUID
  service_name: str
  booking_date: date
  session: str
  num_persons: int
  amount_paise: int
  status: str
  requires_approval: bool
  special_note: str | None
  persons: list[PersonResponse]
  created_at: datetime

BookingListResponse:
  bookings: list[BookingResponse]
  total: int
  page: int
  limit: int
```

#### 2.5 models/schemas/admin.py — Service management schemas (30 min)

Admin-specific schemas for service management. These will be used by your Day 7 admin routes.

#### 2.6 models/schemas/e_undiyal.py + certificate.py (30 min)

Preview schema definitions for Day 4 work (start defining now):

```
DonationInitiateRequest:
  donor_name: str
  donor_phone: str (E.164)
  donor_email: EmailStr | None
  amount_paise: int (ge=100_00)  -- minimum ₹100
  donation_category: str | None

CertificatePreferenceRequest:
  donor_location_type: Literal['local','domestic','international']
  donor_address: DonorAddress | None   -- required if courier delivery

DonorAddress:
  full_name: str
  door_no: str
  street: str
  city: str
  state: str
  pincode: str
  country: str
  phone: str
  pan_number: str | None
```

#### 2.7 Register Public Routers in main.py (15 min)

Notify Abhinav to add to main.py (or do it yourself if you have access):
- `app.include_router(services_router, prefix="/api/v1")`

---

### Day 2 Completion Criteria

- [ ] `GET /api/v1/services` returns all 10 seeded services
- [ ] `GET /api/v1/services/<uuid>` returns correct service
- [ ] `GET /api/v1/services/<invalid-uuid>` returns 404
- [ ] All Pydantic schemas for bookings defined and importable
- [ ] Abhinav can import `BookingCreateRequest` from your schemas file

---

## Day 3 — E-Undiyal Donation Flow

**Focus:** Independent donation initiation and payment flow (never touches booking tables).  
**Estimated Effort:** 7 hours  
**Critical:** This module must NEVER reference `bookings` or `slot_inventory` tables.

### Tasks

#### 3.1 repositories/e_undiyal_repo.py (1 hour)

```
create_transaction(data) → EUndiyalTransaction
  → INSERT INTO e_undiyal_transactions (...) RETURNING *
  → Generate reference: SMV-EU-YYYYMMDD-NNNN (sequential counter per day)

get_transaction(transaction_id) → EUndiyalTransaction
  → SELECT * FROM e_undiyal_transactions WHERE id = ?

get_transaction_by_reference(reference) → EUndiyalTransaction
  → SELECT * WHERE transaction_reference = ?

update_status(transaction_id, status) → None
  → UPDATE e_undiyal_transactions SET status = ?, updated_at = NOW() WHERE id = ?

get_user_transactions(user_id) → list[EUndiyalTransaction]
  → SELECT * WHERE user_id = ? ORDER BY created_at DESC
```

#### 3.2 services/e_undiyal_service.py (3 hours)

```
initiate_donation(request: DonationInitiateRequest, user_id: UUID | None) → DonationInitiateResponse

  1. Validate: amount_paise >= 10000 (minimum ₹100 donation)
  2. Generate transaction_reference: SMV-EU-{YYYYMMDD}-{counter}
  3. e_undiyal_repo.create_transaction({
       user_id, donor_name, donor_phone, donor_email,
       amount_paise, donation_category,
       status: 'initiated',
       tax_certificate_eligible: True,
       certificate_status: 'pending_details'
     })
  4. payment_service.create_order(transaction_id, amount_paise)
     Note: pass transaction reference as receipt, NOT booking_id
  5. payment_repo.create_payment_record(
       e_undiyal_id=transaction_id,
       booking_id=None,
       gateway_order_id=...,
       amount_paise=...
     )
  6. Return { transaction_id, transaction_reference, gateway_order_id, amount_paise,
              razorpay_key_id, message_80g: "This donation qualifies for 80G tax exemption" }

complete_donation(transaction_id: UUID, gateway_payment_id: str) → None
  Called from webhook_service when payment.captured event for E-Undiyal:
  
  1. e_undiyal_repo.update_status(transaction_id, 'success')
  2. Update payments: status='success', gateway_payment_id=...
  3. Trigger 80G workflow: certificate_service.trigger_80g_workflow(transaction_id)
  4. BackgroundTask: notification_service.send_sms(donor_phone,
       "Thank you for your donation of ₹{amount}. Your donation qualifies for
        80G tax exemption. You will be contacted for certificate delivery.")
  5. BackgroundTask: notification_service.send_email(...)
  6. BackgroundTask: audit_service.write_log("donation.completed", ...)
```

#### 3.3 routers/e_undiyal/donate.py (1 hour)

```
POST /api/v1/e-undiyal/initiate
  Auth: Optional (logged-in users have user_id, guests donate anonymously)
  Body: DonationInitiateRequest
  → e_undiyal_service.initiate_donation(request, current_user.id if authenticated)
  → Background: audit_service.write_log("donation.initiated", ...)
  → Return HTTP 201 with DonationInitiateResponse

GET /api/v1/e-undiyal/{transaction_id}
  Auth: require_role("devotee") — only own transactions
  → e_undiyal_repo.get_transaction(transaction_id)
  → Verify: transaction.user_id == current_user.id
  → Return transaction details + certificate status

GET /api/v1/e-undiyal (user's own donation history)
  Auth: require_role("devotee")
  → e_undiyal_repo.get_user_transactions(current_user.id)
```

#### 3.4 Webhook Integration for E-Undiyal (1 hour)

In `webhook_service.process_payment_captured()`:
- Check: is this payment for a booking or E-Undiyal?
  - Look at `payments` table: if `booking_id` is NULL and `e_undiyal_id` is set → E-Undiyal
  - If E-Undiyal: call `e_undiyal_service.complete_donation(transaction_id, ...)`
  - If booking: normal booking confirmation flow

---

### Day 3 Completion Criteria

- [ ] `POST /api/v1/e-undiyal/initiate` creates a transaction + Razorpay order
- [ ] E-Undiyal `payments` record has `booking_id = NULL`, `e_undiyal_id = <uuid>`
- [ ] E-Undiyal tables are completely separate from booking tables
- [ ] Simulate webhook → transaction status = `success`, certificate_status = `pending_details`
- [ ] Donor receives SMS notification
- [ ] `GET /api/v1/e-undiyal/{id}` shows current certificate_status

---

## Day 4 — 80G Certificate Workflow

**Focus:** Location-aware certificate delivery logic.  
**Estimated Effort:** 7 hours

### Tasks

#### 4.1 repositories/certificate_repo.py (1 hour)

```
update_delivery_preference(transaction_id, preference_data) → None
  UPDATE e_undiyal_transactions SET
    delivery_mode = ?,
    donor_location_type = ?,
    donor_address = ?,
    certificate_status = 'processing',
    details_submitted_at = NOW()
  WHERE id = ?

issue_certificate(transaction_id, cert_number, cert_url, admin_id) → None
  UPDATE e_undiyal_transactions SET
    certificate_number = ?,
    certificate_url = ?,
    certificate_status = 'ready',
    certificate_issued_by = ?,
    certificate_issued_at = NOW()
  WHERE id = ?

mark_dispatched(transaction_id, courier_partner, tracking_id) → None
  UPDATE e_undiyal_transactions SET
    courier_partner = ?,
    courier_tracking_id = ?,
    certificate_status = 'dispatched',
    dispatched_at = NOW()
  WHERE id = ?

mark_delivered(transaction_id) → None
  UPDATE SET certificate_status = 'delivered'

get_pending_certificates(status) → list
  SELECT * FROM e_undiyal_transactions
  WHERE certificate_status = ? ORDER BY created_at ASC
```

#### 4.2 services/certificate_service.py (3 hours)

```
trigger_80g_workflow(transaction_id: UUID) → None
  Called from e_undiyal_service after payment success.
  Simply ensures certificate_status = 'pending_details' (already set at creation).
  Sends initial notification to donor with link to submit delivery preference.

process_delivery_preference(transaction_id: UUID, request: CertificatePreferenceRequest) → None

  Validate: transaction exists and certificate_status == 'pending_details'
  (If already submitted → return 409 "Preference already submitted")

  If donor_location_type == 'local':
    delivery_mode = 'in_person'
    certificate_repo.update_delivery_preference(transaction_id, { delivery_mode='in_person', ... })
    notification_service.send_sms(phone,
      "Your 80G certificate will be ready for collection at the temple office.
       Please bring your original payment receipt and a valid photo ID.
       Office hours: 9:00 AM – 5:00 PM, Monday to Saturday.")
    notification_service.send_email(email, ...)

  If donor_location_type == 'domestic':
    Validate: donor_address present, PAN format valid (AAAAA1111A regex)
    Validate: pincode is 6 digits
    certificate_repo.update_delivery_preference(transaction_id, { delivery_mode='courier', donor_address=address, ... })
    notification_service.send_sms(phone,
      "Your 80G certificate will be dispatched to your address via courier
       within 7–10 working days. You will receive a tracking number once dispatched.")

  If donor_location_type == 'international':
    Validate: donor_address present, country code valid
    certificate_repo.update_delivery_preference(transaction_id, { delivery_mode='courier', ... })
    notification_service.send_sms(phone,
      "Your 80G certificate will be dispatched via international courier.
       Delivery typically takes 10–21 working days depending on your country.
       A tracking number will be shared via email once dispatched.")

issue_certificate(transaction_id: UUID, cert_data: dict, admin_id: UUID) → None
  1. Generate certificate_number: SMV-80G-YYYY-NNNN (sequential per financial year)
  2. receipt_service.generate_certificate_pdf(transaction_id, cert_data)
     → Upload to Supabase Storage bucket: 'donation-receipts' (private)
     → Get signed URL (30-day expiry)
  3. certificate_repo.issue_certificate(transaction_id, cert_number, signed_url, admin_id)
  4. notification_service.send_sms(phone,
       "Your 80G certificate (No: SMV-80G-2026-0042) is ready.
        Download: {signed_url}")
  5. notification_service.send_email(email, certificate_url=signed_url)
  6. audit_service.write_log("certificate.issued", ...)
```

#### 4.3 routers/e_undiyal/certificate.py (1 hour)

```
POST /api/v1/e-undiyal/{transaction_id}/certificate-preference
  Auth: Optional (signed link for guests OR JWT for logged-in)
  Body: CertificatePreferenceRequest
  → certificate_service.process_delivery_preference(transaction_id, request)
  → Return: { message: "Preference submitted. ...<delivery-specific message>" }

GET /api/v1/e-undiyal/{transaction_id}/certificate-status
  Auth: require_role("devotee") or admin
  → certificate_repo.get_certificate_status(transaction_id)
  → Return: { certificate_status, delivery_mode, courier_tracking_id, certificate_url }
```

#### 4.4 Admin Certificate Management API Stubs (1 hour)

These will be fleshed out on Day 7, but create the route files now:

```
GET  /admin/certificates?status=processing
POST /admin/certificates/{id}/issue
POST /admin/certificates/{id}/dispatch
POST /admin/certificates/{id}/collected
```

---

### Day 4 Completion Criteria

- [ ] Donor can submit delivery preference (local/domestic/international)
- [ ] Local → in_person delivery mode, correct SMS sent
- [ ] Domestic → courier delivery, PAN validation enforced, correct SMS sent
- [ ] International → courier, correct SMS sent
- [ ] Duplicate preference submission → 409 "Already submitted"
- [ ] Admin can call `issue_certificate` → certificate_status = `ready`
- [ ] Donor notified with certificate download link

---

## Day 5 — Notice Management System

**Focus:** Full notice lifecycle — draft, schedule, publish, expire.  
**Estimated Effort:** 6 hours

### Tasks

#### 5.1 repositories/notice_repo.py (1 hour)

```
get_active_notices() → list[Notice]
  SELECT * FROM notices
  WHERE status = 'active'
    AND (expires_at IS NULL OR expires_at > NOW())
  ORDER BY priority DESC, published_at DESC

get_all_notices(status_filter) → list[Notice]
  SELECT * FROM notices
  WHERE (? IS NULL OR status = ?)
  ORDER BY created_at DESC

get_notice(notice_id) → Notice | None
  SELECT * FROM notices WHERE id = ?

create_notice(data) → Notice
  INSERT INTO notices (...) RETURNING *

update_notice(notice_id, data) → Notice
  UPDATE notices SET ... WHERE id = ?

activate_notice(notice_id) → None
  UPDATE notices SET status = 'active' WHERE id = ?

deactivate_notice(notice_id) → None
  UPDATE notices SET status = 'expired' WHERE id = ?

delete_notice(notice_id) → None
  DELETE FROM notices WHERE id = ?

activate_scheduled() → int
  UPDATE notices SET status='active'
  WHERE status='scheduled' AND published_at <= NOW()
  RETURNING COUNT(*)

expire_old() → int
  UPDATE notices SET status='expired'
  WHERE status='active' AND expires_at IS NOT NULL AND expires_at < NOW()
  RETURNING COUNT(*)
```

#### 5.2 services/notice_service.py (1 hour)

```
get_public_notices() → list[Notice]
  → notice_repo.get_active_notices()

create_notice(admin_id, data) → Notice
  → Validate: if published_at in past AND status='scheduled' → auto-activate
  → notice_repo.create_notice(data)
  → audit_service.write_log("notice.created", ...)

update_notice(notice_id, data) → Notice
  → notice_repo.update_notice(notice_id, data)
  → audit_service.write_log("notice.updated", ...)

activate_now(notice_id) → None
  → notice_repo.activate_notice(notice_id)
  → audit_service.write_log("notice.activated", ...)

deactivate_now(notice_id) → None
  → notice_repo.deactivate_notice(notice_id)
  → audit_service.write_log("notice.deactivated", ...)

run_scheduler() → None
  Called by APScheduler every 5 minutes:
  → n_activated = notice_repo.activate_scheduled()
  → n_expired = notice_repo.expire_old()
  → log.info(f"Notices: activated={n_activated}, expired={n_expired}")
```

#### 5.3 routers/public/notices.py (30 min)

```
GET /api/v1/notices
  No auth required.
  → notice_service.get_public_notices()
  → Return: list of active notices with title, body, category, priority
```

#### 5.4 routers/admin/notices.py (2 hours)

All routes require `require_role("admin")`.

```
GET    /admin/notices?status=active|draft|scheduled|expired
GET    /admin/notices/{id}
POST   /admin/notices         Body: { title, title_tamil, body, body_tamil, category, priority, published_at, expires_at }
PUT    /admin/notices/{id}    Body: Same fields (all optional)
PATCH  /admin/notices/{id}/activate
PATCH  /admin/notices/{id}/deactivate
DELETE /admin/notices/{id}   → Soft delete: set status='expired'
```

#### 5.5 models/schemas/notice.py (30 min)

```
NoticeCreateRequest: { title, title_tamil, body, body_tamil, category, priority, published_at, expires_at }
NoticeResponse: { id, title, body, category, status, priority, published_at, expires_at, created_at }
```

---

### Day 5 Completion Criteria

- [ ] `GET /api/v1/notices` returns only active notices
- [ ] `POST /admin/notices` creates draft notice
- [ ] `PATCH /admin/notices/{id}/activate` → notice becomes active, appears in public API
- [ ] Scheduler: notice with `published_at` in past → becomes active on next scheduler run
- [ ] Scheduler: notice past `expires_at` → becomes expired, removed from public API
- [ ] Deactivated notice → removed from public API immediately
- [ ] All admin notice operations write to audit_log

---

## Day 6 — E-Undiyal Admin + User Management APIs

**Focus:** Admin management of E-Undiyal donations and user management.  
**Estimated Effort:** 6 hours

### Tasks

#### 6.1 Admin E-Undiyal API (2 hours)

```
GET    /admin/e-undiyal?status=success&date=2026-08-01
  → List all transactions with filters
  → Include certificate_status

GET    /admin/e-undiyal/{transaction_id}
  → Full transaction detail + certificate status

POST   /admin/certificates/{transaction_id}/issue
  Body: { certificate_data: {} }
  → certificate_service.issue_certificate(transaction_id, cert_data, current_admin.id)

POST   /admin/certificates/{transaction_id}/dispatch
  Body: { courier_partner, courier_tracking_id }
  → certificate_repo.mark_dispatched(...)
  → notification_service.send_sms(phone, "Your certificate has been dispatched. Tracking: {tracking_id}")

POST   /admin/certificates/{transaction_id}/collected
  (For in-person pickup)
  → certificate_repo.mark_delivered(transaction_id)
  → audit_service.write_log("certificate.collected", ...)

GET    /admin/certificates?status=processing
  → certificate_repo.get_pending_certificates('processing')
```

#### 6.2 repositories/user_repo.py (1 hour)

```
get_user(user_id) → User | None
  SELECT * FROM users WHERE id = ?

get_all_users(page, limit, role_filter) → list[User]
  SELECT * FROM users WHERE (? IS NULL OR role = ?) ORDER BY created_at DESC LIMIT ? OFFSET ?

search_users(query) → list[User]
  SELECT * FROM users WHERE phone ILIKE ? OR email ILIKE ? OR full_name ILIKE ?

update_user_role(user_id, role) → None
  UPDATE users SET role = ? WHERE id = ?

deactivate_user(user_id) → None
  UPDATE users SET is_active = FALSE WHERE id = ?

get_user_booking_summary(user_id) → dict
  SELECT COUNT(*), SUM(amount_paise), ... FROM bookings WHERE user_id = ?
```

#### 6.3 routers/admin/users.py (2 hours)

All routes require `require_role("admin")`. Role changes require `require_role("super_admin")`.

```
GET    /admin/users?page=1&limit=20&role=devotee
GET    /admin/users/search?q=phone_or_email
GET    /admin/users/{user_id}
GET    /admin/users/{user_id}/bookings    → user's booking history
GET    /admin/users/{user_id}/donations   → user's E-Undiyal donations
PATCH  /admin/users/{user_id}/role        → super_admin only
PATCH  /admin/users/{user_id}/deactivate  → admin
```

#### 6.4 models/schemas/admin.py — User schemas (30 min)

```
UserAdminResponse: { id, phone, email, full_name, role, is_active, created_at, booking_count, donation_total }
UserRoleUpdateRequest: { role: Literal['devotee','staff','admin','super_admin'] }
```

---

### Day 6 Completion Criteria

- [ ] Admin can list all donations
- [ ] Admin can issue certificate → donor notified
- [ ] Admin can mark as dispatched → donor gets tracking SMS
- [ ] Admin can list all users with pagination
- [ ] Super admin can change user role → logged in audit
- [ ] Admin cannot change role (only super_admin can)

---

## Day 7 — Admin Booking Management + Services API

**Focus:** Admin oversight of bookings, approval workflow, services management.  
**Estimated Effort:** 7 hours

### Tasks

#### 7.1 Admin Booking Management API (3 hours)

```
GET    /admin/bookings?status=pending_approval&date=2026-08-01&service_id=<uuid>&page=1
  → booking_repo.get_all_bookings(filters)
  → Return paginated list with user info and service name

GET    /admin/bookings/{booking_id}
  → booking_repo.get_booking(booking_id)
  → Return full detail with persons list, payment info

POST   /admin/bookings/{booking_id}/approve
  Auth: require_role("admin")
  Body: { note: str }
  → Verify booking.status == 'pending_approval'
  → UPDATE bookings SET status='approved', approved_by=admin_id, approved_at=NOW(), approval_note=note
  → UPDATE slot_inventory: no change (already confirmed)
  → notification_service.send_sms(user_phone, "Your booking has been approved!")
  → audit_service.write_log("booking.approved", ...)

POST   /admin/bookings/{booking_id}/reject
  Auth: require_role("admin")
  Body: { reason: str }
  → Verify booking.status IN ('pending_payment','pending_approval')
  → UPDATE bookings SET status='rejected'
  → UPDATE slot_inventory: confirmed_count -= 1
  → payment_service.initiate_refund(payment_id, amount) if payment was made
  → notification_service.send_sms(user_phone, "Your booking has been rejected. Reason: {reason}")
  → audit_service.write_log("booking.rejected", ...)

POST   /admin/bookings/{booking_id}/cancel
  Auth: require_role("admin")
  Body: { reason: str }
  → UPDATE bookings SET status='cancelled'
  → Refund if applicable
  → notification_service.send_sms(...)
  → audit_service.write_log("booking.cancelled", ...)

GET    /admin/bookings/pending-approvals
  → Get all bookings with status='pending_approval' ordered by created_at
```

#### 7.2 Admin Services Management API (2 hours)

```
GET    /admin/services
  → service_repo.get_all_services(active_only=False)
  → Includes both active and inactive

GET    /admin/services/{service_id}
GET    /admin/services/{service_id}/bookings?date=2026-08-01
  → Bookings for this service on a date

POST   /admin/services
  Auth: require_role("super_admin")
  → service_repo.create_service(data)
  → audit_service.write_log("service.created", ...)

PUT    /admin/services/{service_id}
  Auth: require_role("super_admin")
  → service_repo.update_service(service_id, data)
  → audit_service.write_log("service.updated", ...)

PATCH  /admin/services/{service_id}/toggle
  Auth: require_role("super_admin")
  → service_repo.toggle_active(service_id, ...)
  → audit_service.write_log("service.toggled", ...)
```

#### 7.3 Admin Slot Inventory API (1 hour)

```
GET    /admin/inventory?service_id=<uuid>&start_date=2026-08-01&end_date=2026-08-31
  → slot_repo queries for date range
  → Return: list of { date, session, total_capacity, confirmed, pending, available }

PATCH  /admin/inventory/{slot_id}/block
  Auth: require_role("admin")
  Body: { reason: str }
  → slot_repo.block_slot(slot_id, reason)
  → audit_service.write_log("slot.blocked", ...)

PATCH  /admin/inventory/{slot_id}/capacity
  Auth: require_role("super_admin")
  Body: { total_capacity: int }
  → UPDATE slot_inventory SET total_capacity = ?
```

---

### Day 7 Completion Criteria

- [ ] `GET /admin/bookings` returns all bookings with filters
- [ ] `POST /admin/bookings/{id}/approve` → status=approved, donor SMS sent
- [ ] `POST /admin/bookings/{id}/reject` → status=rejected, slot released, refund initiated
- [ ] Admin can view pending-approval queue
- [ ] Super admin can create/update services
- [ ] Admin can view slot inventory for any date range
- [ ] All admin actions write to audit_log

---

## Day 8 — Reporting System

**Focus:** Daily, weekly, monthly reports + dashboard KPIs.  
**Estimated Effort:** 7 hours

### Tasks

#### 8.1 services/report_service.py (4 hours)

All queries are READ ONLY. No writes to business tables.

```
get_daily_summary(date) → DailySummary
  → Total bookings by status (confirmed/pending/rejected/cancelled)
  → Total revenue (sum of amount_paise for confirmed bookings)
  → Bookings per service
  → Total donations (E-Undiyal)
  → Total donation amount
  → Conflict events triggered (from audit_logs)

get_weekly_trend(start_date, end_date) → WeeklyTrend
  → Day-by-day booking volumes
  → Revenue per day
  → Occupancy rate per service per day

get_monthly_report(year, month) → MonthlyReport
  → Gross revenue
  → Net revenue (after refunds)
  → Service performance (most booked, occupancy rates)
  → New user registrations
  → E-Undiyal totals

get_service_occupancy(service_id, start_date, end_date) → OccupancyReport
  → Booked vs available slots per date
  → Average occupancy percentage

get_certificate_report(start_date, end_date) → CertificateReport
  → Certificates by status (pending/processing/ready/dispatched/delivered)
  → International vs domestic breakdown

get_dashboard_kpis() → DashboardKPIs
  → Bookings today (total, confirmed, pending)
  → Revenue today
  → Active notices count
  → Slots nearing capacity (> 80% full) — alerts
  → Pending approvals count
  → Pending certificate issuances count
  → E-Undiyal today (count + amount)
```

#### 8.2 routers/admin/reports.py (2 hours)

All routes require `require_role("staff")` or higher.

```
GET /admin/reports/dashboard
  → report_service.get_dashboard_kpis()
  → Real-time admin dashboard data

GET /admin/reports/daily?date=2026-08-01
  → report_service.get_daily_summary(date)

GET /admin/reports/weekly?start=2026-08-01&end=2026-08-07
  → report_service.get_weekly_trend(start, end)

GET /admin/reports/monthly?year=2026&month=8
  → report_service.get_monthly_report(year, month)

GET /admin/reports/occupancy?service_id=<uuid>&start=?&end=?
  → report_service.get_service_occupancy(...)

GET /admin/reports/certificates?start=?&end=?
  → report_service.get_certificate_report(...)

GET /admin/reports/audit-log?action=&entity_type=&start=&end=
  Auth: require_role("admin")
  → Direct query on audit_logs with filters (READ ONLY)
  → Paginated, last 1000 records max per request
```

#### 8.3 models/schemas/report.py (30 min)

Define all report response schemas:
```
DashboardKPIs, DailySummary, WeeklyTrend, MonthlyReport, OccupancyReport, CertificateReport
```

---

### Day 8 Completion Criteria

- [ ] `GET /admin/reports/dashboard` returns live KPI data
- [ ] `GET /admin/reports/daily?date=today` returns correct booking counts
- [ ] Revenue figures match actual `payments` table sums
- [ ] Certificate report shows correct status breakdowns
- [ ] Audit log query returns filterable results
- [ ] Staff role can access reports (not blocked)
- [ ] All queries are READ ONLY (verified via query review)

---

## Day 9 — Unit Tests: E-Undiyal + Certificate + Services

**Estimated Effort:** 7 hours

### 9.1 tests/unit/test_e_undiyal.py
- Initiate donation → transaction created, payment order returned
- Donation minimum amount enforced (< ₹100 → 422)
- Complete donation → status=success, certificate_status=pending_details
- Guest donation (no user_id) → works correctly
- E-Undiyal payment record has booking_id=NULL

### 9.2 tests/unit/test_certificate.py
- Local preference → in_person delivery, correct SMS content
- Domestic preference: no PAN → 422
- Domestic preference: invalid PAN format → 422
- Domestic preference: valid PAN → processing
- International preference → processing
- Duplicate preference submission → 409
- Admin issues certificate → status=ready, donor notified

### 9.3 tests/unit/test_notices.py
- Create draft → not in public API
- Activate → appears in public API
- Schedule with future date → not yet active
- Scheduler runs → scheduled notice becomes active
- Expired notices removed from public API

### 9.4 tests/unit/test_services.py
- GET /api/v1/services → returns only active services
- Inactive service excluded from public list
- Admin can see inactive services
- Super admin can toggle active status

---

### Day 9 Completion Criteria

- [ ] `pytest tests/unit/test_e_undiyal.py` → all pass
- [ ] `pytest tests/unit/test_certificate.py` → all pass
- [ ] `pytest tests/unit/test_notices.py` → all pass
- [ ] `pytest tests/unit/test_services.py` → all pass
- [ ] Test coverage > 80% for e_undiyal_service and certificate_service

---

## Day 10 — Unit Tests: Admin APIs + RBAC

**Estimated Effort:** 7 hours

### 10.1 tests/unit/test_admin_rbac.py

- Devotee token on `/admin/bookings` → 403
- Staff token on `/admin/reports/dashboard` → 200
- Staff token on `/admin/bookings/{id}/approve` → 403
- Admin token on `/admin/bookings/{id}/approve` → 200
- Admin token on `/admin/services` (POST) → 403
- Super admin token on `/admin/services` (POST) → 201
- Admin token on `/admin/users/{id}/role` (PATCH) → 403
- Super admin token on `/admin/users/{id}/role` → 200
- No token on `/admin/*` → 401

### 10.2 tests/unit/test_booking_management.py

- Approve pending_approval booking → status=approved
- Approve already-confirmed booking → 409
- Reject booking → status=rejected, slot released
- Cancel confirmed booking → refund initiated
- Admin filters work (by status, date, service_id)

### 10.3 tests/unit/test_reports.py

- Dashboard KPIs return all expected fields
- Daily summary totals match test data
- Occupancy report for service with no bookings → 0%

---

### Day 10 Completion Criteria

- [ ] All RBAC tests pass — no unauthorized access works
- [ ] Admin approval workflow tests pass
- [ ] Report endpoints return correct data structure
- [ ] `pytest tests/unit/test_admin_rbac.py` → all 18 tests pass

---

## Day 11 — Integration Tests: E-Undiyal + Certificate Full Flow

**Estimated Effort:** 7 hours

### 11.1 tests/integration/test_e_undiyal_flow.py

Full integration test:
1. POST /api/v1/e-undiyal/initiate → get gateway_order_id
2. Simulate webhook (payment.captured for E-Undiyal payment)
3. GET /api/v1/e-undiyal/{id} → status=success, cert_status=pending_details
4. POST /api/v1/e-undiyal/{id}/certificate-preference (local)
5. GET /api/v1/e-undiyal/{id}/certificate-status → cert_status=processing
6. POST /admin/certificates/{id}/issue
7. GET /api/v1/e-undiyal/{id}/certificate-status → cert_status=ready

### 11.2 tests/integration/test_admin_workflow.py

1. Create test booking via API
2. Simulate payment webhook → pending_approval
3. Admin approves → status=approved
4. Create another booking → reject it → verify slot released
5. Create new booking for same slot → succeeds

### 11.3 tests/integration/test_notice_lifecycle.py

1. Create scheduled notice with published_at = 1 minute ago
2. Run scheduler manually
3. Verify notice appears in public API
4. Set expires_at = 1 minute ago
5. Run scheduler
6. Verify notice removed from public API

---

### Day 11 Completion Criteria

- [ ] Full E-Undiyal → certificate integration test passes
- [ ] Admin approval workflow integration test passes
- [ ] Notice lifecycle integration test passes
- [ ] All audit_log entries present for each step

---

## Day 12 — Final Bug Fixes + Admin API Polish

**Estimated Effort:** 6 hours

### 12.1 Bug Fixes from Day 11 Test Results

Fix any issues found in integration tests. Prioritize:
1. Incorrect HTTP status codes
2. Missing audit log entries
3. Wrong notification content
4. Role guard gaps

### 12.2 Admin API Polish

- Ensure consistent pagination on all list endpoints
- Verify all admin endpoints produce correct HTTP status codes (201 for creates, 200 for updates, 204 for deletes)
- Add missing error responses (404 when resource not found)
- Ensure admin audit log is written for every admin action (double-check all routes)

### 12.3 Performance Review

- Run `EXPLAIN ANALYZE` on the 5 slowest admin queries
- Add missing database indexes if needed
- Verify report queries return within 2 seconds for 1-month date range

---

### Day 12 Completion Criteria

- [ ] All integration tests pass (zero failures)
- [ ] All admin list endpoints have working pagination
- [ ] All admin write actions produce audit log entries
- [ ] Report queries return within 2 seconds

---

## Day 13 — Staging Testing + UAT

**Estimated Effort:** 6 hours

### 13.1 Deploy Your Modules to Staging

Work with Abhinav who manages deployment. Verify your modules work on staging:

**Staging smoke tests (your modules):**
1. `GET https://staging-api.smvd.in/api/v1/services` → 10 services returned
2. `GET https://staging-api.smvd.in/api/v1/notices` → notices returned
3. `POST /api/v1/e-undiyal/initiate` → creates transaction
4. `GET /admin/reports/dashboard` → KPIs returned
5. Admin approve/reject booking flow

### 13.2 Admin Portal UAT Walkthrough

Work with temple admin staff (if available) to test:
1. Login flow + 2FA
2. View bookings + approve/reject
3. Create/manage notices
4. View certificate queue + issue certificate
5. View reports dashboard

### 13.3 Final Data Verification

Verify seed data in staging:
- All 10 services exist and have correct prices
- All conflict rules seeded correctly
- No dummy/test data in staging

---

### Day 13 Completion Criteria

- [ ] All your modules work on staging URL
- [ ] Services list correct on staging
- [ ] E-Undiyal flow works on staging
- [ ] Reports return data on staging
- [ ] Admin UAT walkthrough complete (or documented as pending)

---

## Day 14 — Production Support + Final Checklist

**Estimated Effort:** 6 hours

### 14.1 Production Data Setup

- Seed all 10 services with final confirmed prices in production
- Seed conflict rules in production
- Verify admin users created with 2FA enabled

### 14.2 Production Verification

Test your modules in production:
1. Services API returns correct data
2. Admin login + 2FA works
3. Notices created correctly
4. Reports show zero data initially (correct for fresh deployment)
5. E-Undiyal flow works with live Razorpay

### 14.3 Production Checklist — Your Modules

- [ ] All 10 services seeded with correct prices in production
- [ ] Conflict rules seeded in production
- [ ] Admin users created with 2FA enabled in production
- [ ] E-Undiyal 80G certificate flow tested in production
- [ ] Notice management tested in production
- [ ] Reports dashboard accessible and returning data
- [ ] All admin APIs protected by correct role guards in production
- [ ] Monitoring: verify Sentry captures your module's errors correctly

---

## Summary: Athreyan Module Ownership

| Module | Files | Days |
|--------|-------|------|
| All DB Migrations (11 files) | migrations/versions/*.py | Day 1 |
| Services Catalogue | repositories/service_repo.py, routers/public/services.py | Day 2 |
| Pydantic Schemas | models/schemas/*.py (all) | Day 2 |
| E-Undiyal Donation | services/e_undiyal_service.py, routers/e_undiyal/donate.py | Day 3 |
| 80G Certificate | services/certificate_service.py, routers/e_undiyal/certificate.py | Day 4 |
| Notice Management | services/notice_service.py, routers/admin/notices.py, routers/public/notices.py | Day 5 |
| Admin E-Undiyal + User Mgmt | routers/admin/users.py, routers/admin/certificates.py | Day 6 |
| Admin Bookings + Services + Inventory | routers/admin/bookings.py, routers/admin/services.py | Day 7 |
| Reporting System | services/report_service.py, routers/admin/reports.py | Day 8 |
| Unit Tests (your modules) | tests/unit/test_e_undiyal, notices, services, admin_rbac | Days 9–10 |
| Integration Tests | tests/integration/test_e_undiyal_flow.py, admin_workflow.py | Day 11 |
| Bug fixes + polish | All your modules | Day 12 |
| Staging UAT | Staging environment | Day 13 |
| Production setup | Production seed + verification | Day 14 |
