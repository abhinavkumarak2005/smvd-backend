# Sri Manakula Vinayagar Devasthanam — Backend Architecture & Implementation Plan

**Document Type:** Production Architecture & Implementation Plan  
**Version:** 1.0  
**Date:** June 2026  
**Classification:** Internal — Engineering Team  
**Scope:** Backend only (FastAPI + Supabase). Frontend is a separate project.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technology Stack Rationale](#2-technology-stack-rationale)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Database Architecture](#4-database-architecture)
5. [Authentication & Authorization Architecture](#5-authentication--authorization-architecture)
6. [Service Catalogue & Business Rules](#6-service-catalogue--business-rules)
7. [Booking Engine Architecture](#7-booking-engine-architecture)
8. [E-Undiyal Architecture](#8-e-undiyal-architecture)
9. [Calendar Management System](#9-calendar-management-system)
10. [Payment Integration Layer](#10-payment-integration-layer)
11. [CMS / Super Admin Portal Architecture](#11-cms--super-admin-portal-architecture)
12. [Notice Management System](#12-notice-management-system)
13. [Reporting & Analytics System](#13-reporting--analytics-system)
14. [User Management System](#14-user-management-system)
15. [FastAPI Application Architecture](#15-fastapi-application-architecture)
16. [Supabase Architecture](#16-supabase-architecture)
17. [Security Architecture](#17-security-architecture)
18. [Deployment Architecture](#18-deployment-architecture)
19. [Testing Strategy](#19-testing-strategy)
20. [3-Day Implementation Roadmap](#20-3-day-implementation-roadmap)
21. [Production Readiness Checklist](#21-production-readiness-checklist)

---

## 1. Executive Summary

This document defines the complete backend architecture for the Sri Manakula Vinayagar Devasthanam digital platform. The system provides a secure, scalable, and fully auditable temple booking and operations platform.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Backend Authority** | All business rules, validations, and conflict checks are enforced exclusively on the backend. The frontend is never trusted for any business-critical decision. |
| **Zero Overbooking** | Atomic transactions and database-level constraints guarantee slot capacity is never exceeded. |
| **Audit Trail** | Every write operation produces an immutable audit log entry. |
| **Separation of Concerns** | E-Undiyal, Bookings, Calendar, Notices, and Reporting are independent subsystems communicating via well-defined internal contracts. |
| **Defense in Depth** | Multiple security layers — RLS, JWT validation, rate limiting, input validation, and monitoring — operate independently. |

### High-Level System Modules

```
┌─────────────────────────────────────────────────────────────┐
│                  Sri Manakula Platform                       │
├──────────────┬──────────────┬───────────────┬───────────────┤
│  Public API  │  Booking API │  CMS API      │  Payment API  │
├──────────────┴──────────────┴───────────────┴───────────────┤
│                    FastAPI Application                       │
├──────────────────────────────────────────────────────────────┤
│         Supabase (PostgreSQL + Auth + Storage + RLS)         │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack Rationale

### Why FastAPI

FastAPI is selected as the primary backend framework for the following reasons:

| Reason | Detail |
|--------|--------|
| **Async-Native** | Built on Starlette and asyncio. All database I/O, payment callbacks, and external API calls are non-blocking, enabling high concurrency. |
| **Automatic Validation** | Pydantic models enforce strict input validation on every request before any business logic executes. This eliminates a full class of injection and malformed-data vulnerabilities. |
| **Auto-Generated OpenAPI** | Swagger UI and ReDoc are available out of the box, enabling backend testing without a frontend. |
| **Performance** | Benchmarks consistently show FastAPI near the top of Python web frameworks in requests/second. |
| **Type Safety** | Python type hints provide compile-time-like safety and enable IDE-level error detection. |
| **Middleware Ecosystem** | Rate limiting, CORS, authentication middleware, and structured logging are first-class citizens. |
| **Background Tasks** | Native support for background task execution (post-payment actions, email sending, audit writes). |
| **Dependency Injection** | Built-in DI system makes auth guard injection, database session injection, and configuration injection clean and testable. |

### What FastAPI Is Responsible For

- All HTTP request handling and routing
- Business rule validation and enforcement
- Booking conflict detection and prevention
- Payment webhook processing and verification
- JWT token verification and role extraction
- Supabase database write operations
- Audit log creation
- Background job orchestration
- Admin CMS API endpoints
- Scheduled task management

### Why Supabase

| Reason | Detail |
|--------|--------|
| **PostgreSQL Foundation** | Full ACID compliance, transactions, row locking — all required for a zero-overbooking booking system. |
| **Row Level Security** | Database-level access control ensures data isolation between roles even if application-level auth is bypassed. |
| **Managed Auth** | Supabase Auth handles OTP (SMS), email/password, and JWT issuance, reducing implementation complexity. |
| **Storage** | Managed S3-compatible storage for receipts, media, and report exports. |
| **Realtime** | Optional realtime subscriptions for admin dashboard live updates. |
| **Managed Infrastructure** | No DBA overhead for patching, vacuuming, or connection pooling (PgBouncer is included). |

---

## 3. System Architecture Overview

### Component Diagram

```
                        ┌─────────────────┐
                        │   Public CDN    │
                        │  (CloudFront /  │
                        │   Cloudflare)   │
                        └────────┬────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      API Gateway /       │
                    │   Reverse Proxy (Nginx)  │
                    │  + Rate Limiter          │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │         FastAPI Application          │
              │  ┌──────────┐  ┌──────────────────┐ │
              │  │ Public   │  │   Admin / CMS    │ │
              │  │ API      │  │   API            │ │
              │  │ Router   │  │   Router         │ │
              │  └──────────┘  └──────────────────┘ │
              │  ┌──────────────────────────────────┐│
              │  │      Booking Engine              ││
              │  │  Conflict Checker · Slot Manager ││
              │  │  Capacity Guard · Rule Enforcer  ││
              │  └──────────────────────────────────┘│
              │  ┌──────────────────────────────────┐│
              │  │      Payment Engine              ││
              │  │  Webhook Handler · Receipt Gen   ││
              │  └──────────────────────────────────┘│
              └──────────────────┬──────────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │              Supabase                │
              │  ┌──────────┐  ┌────────────────┐   │
              │  │PostgreSQL│  │  Supabase Auth │   │
              │  │  + RLS   │  │  (JWT/OTP)     │   │
              │  └──────────┘  └────────────────┘   │
              │  ┌──────────────────────────────────┐│
              │  │      Supabase Storage            ││
              │  │  Receipts · Reports · Media      ││
              │  └──────────────────────────────────┘│
              └─────────────────────────────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │       External Payment Gateway       │
              │         (Razorpay / PayU)            │
              └─────────────────────────────────────┘
```

### Request Lifecycle

```
User Request
    │
    ▼
Nginx (TLS Termination + Rate Limiting)
    │
    ▼
FastAPI Middleware Stack
    ├── CORS Check
    ├── JWT Verification
    ├── Role Extraction
    └── Request Logging
    │
    ▼
Route Handler
    ├── Pydantic Input Validation
    ├── Business Rule Validation
    ├── Conflict Check (Database)
    ├── Slot Availability Check (Atomic)
    └── Response Formation
    │
    ▼
Supabase PostgreSQL (via asyncpg)
    │
    ▼
Audit Log Write (Background Task)
    │
    ▼
Response to Client
```

---

## 4. Database Architecture

### Schema Design Principles

- All tables use UUID primary keys.
- All tables include `created_at` and `updated_at` timestamps with automatic triggers.
- Soft deletes are used where data must be preserved for audit (bookings, payments, users).
- Capacity management uses a dedicated `slot_inventory` table with row-level locking (`SELECT FOR UPDATE`) to guarantee atomicity.
- All monetary values are stored as integers in the smallest currency unit (paise).
- Conflict rules are stored as data (not hardcoded), enabling admin configuration.

---

### Core Table Descriptions

#### `users`

Mirrors Supabase Auth users. Extended with temple-specific profile fields.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Supabase Auth user ID |
| `full_name` | TEXT | Devotee's full name |
| `phone` | TEXT UNIQUE | Mobile number (verified via OTP) |
| `email` | TEXT | Email address |
| `is_active` | BOOLEAN | Account status; false = disabled |
| `role` | ENUM | `devotee`, `staff`, `admin`, `super_admin` |
| `created_at` | TIMESTAMPTZ | Registration timestamp |
| `last_login_at` | TIMESTAMPTZ | Last login timestamp |

---

#### `services`

Master catalogue of all bookable temple services.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Service identifier |
| `name` | TEXT | Service name |
| `category` | ENUM | `abhisegam`, `homam`, `kavasam`, `kaapu`, `chariot`, `annadhanam`, `thirukalyanam` |
| `is_active` | BOOLEAN | Whether bookings are currently allowed |
| `price_paise` | INTEGER | Price in paise |
| `advance_booking_days` | INTEGER | Minimum days in advance required |
| `max_families` | INTEGER NULLABLE | For family-based services like Moolavar Abishegam |
| `max_persons_per_family` | INTEGER NULLABLE | Persons per family cap |
| `max_persons_per_booking` | INTEGER | General person cap per booking (max 5) |
| `max_slots_per_session` | INTEGER | Slot capacity per session |
| `session` | ENUM NULLABLE | `morning`, `evening`, `all_day`, `session_1`, `session_2`, `session_3` |
| `conflict_group` | TEXT NULLABLE | Used for mutual exclusivity (e.g., `kaapu_kavasam`) |
| `requires_admin_approval` | BOOLEAN | Triggers manual workflow |
| `notes` | TEXT | Admin notes |
| `updated_by` | UUID FK | Last admin to modify |

---

#### `slot_inventory`

The central capacity ledger. This is the authoritative source of truth for available slots. All booking attempts lock a row here with `SELECT FOR UPDATE`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `service_id` | UUID FK | References `services` |
| `date` | DATE | The booking date |
| `session` | TEXT | Session identifier |
| `total_capacity` | INTEGER | Maximum allowed bookings/families |
| `confirmed_count` | INTEGER | Current confirmed bookings |
| `pending_count` | INTEGER | Bookings awaiting payment (held for TTL) |
| `is_blocked` | BOOLEAN | Admin override: fully block this slot |
| `block_reason` | TEXT NULLABLE | Reason for block |
| `updated_at` | TIMESTAMPTZ | — |

**Key Constraint:** `confirmed_count + pending_count <= total_capacity` enforced at application layer with row lock.

---

#### `bookings`

The master booking record.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `booking_reference` | TEXT UNIQUE | Human-readable reference (e.g., `SMV-20260620-0042`) |
| `user_id` | UUID FK | Booking user |
| `service_id` | UUID FK | Service booked |
| `date` | DATE | Requested date |
| `session` | TEXT | Session |
| `num_persons` | INTEGER | Total persons (≤ 5) |
| `num_families` | INTEGER NULLABLE | For family-based services |
| `persons_per_family` | INTEGER NULLABLE | For Moolavar Abishegam |
| `status` | ENUM | `pending_payment`, `confirmed`, `cancelled`, `rejected`, `refunded` |
| `payment_id` | UUID FK NULLABLE | References `payments` |
| `requires_approval` | BOOLEAN | Flags for admin review |
| `approved_by` | UUID FK NULLABLE | Admin who approved |
| `approved_at` | TIMESTAMPTZ NULLABLE | — |
| `cancellation_reason` | TEXT NULLABLE | — |
| `cancelled_by` | UUID FK NULLABLE | — |
| `post_booking_info` | JSONB NULLABLE | e.g., Kaapu timing info |
| `created_at` | TIMESTAMPTZ | — |
| `updated_at` | TIMESTAMPTZ | — |

---

#### `booking_persons`

Individual persons associated with a booking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `booking_id` | UUID FK | — |
| `family_index` | INTEGER NULLABLE | Family group number (for Moolavar Abishegam) |
| `name` | TEXT | Person's name |
| `star` | TEXT | Nakshatra / birth star |
| `gothram` | TEXT NULLABLE | — |

---

#### `payments`

Tracks all payment attempts and their outcomes.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `booking_id` | UUID FK | — |
| `gateway` | TEXT | `razorpay`, `payu`, etc. |
| `gateway_order_id` | TEXT | Order ID from gateway |
| `gateway_payment_id` | TEXT NULLABLE | Payment ID after success |
| `amount_paise` | INTEGER | Charged amount |
| `status` | ENUM | `initiated`, `success`, `failed`, `refunded` |
| `webhook_payload` | JSONB | Raw webhook data (for audit) |
| `refund_id` | TEXT NULLABLE | Gateway refund reference |
| `refund_amount_paise` | INTEGER NULLABLE | — |
| `refunded_at` | TIMESTAMPTZ NULLABLE | — |
| `created_at` | TIMESTAMPTZ | — |

---

#### `e_undiyal_transactions`

E-Undiyal is a donation mechanism. It is **not a booking** and exists entirely independently.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `transaction_reference` | TEXT UNIQUE | Human-readable ref (e.g., `SMV-EU-20260620-0001`) |
| `user_id` | UUID FK NULLABLE | Logged-in user, or null for guest |
| `donor_name` | TEXT | Name for receipt |
| `donor_phone` | TEXT | — |
| `donor_email` | TEXT NULLABLE | — |
| `amount_paise` | INTEGER | Donation amount |
| `payment_id` | UUID FK | — |
| `status` | ENUM | `initiated`, `success`, `failed` |
| `receipt_url` | TEXT NULLABLE | Supabase Storage URL |
| `created_at` | TIMESTAMPTZ | — |

---

#### `calendar_dates`

Admin-configured date overrides and instructions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `date` | DATE UNIQUE | Calendar date |
| `status` | ENUM | `open`, `blocked`, `partial` |
| `allowed_service_ids` | UUID[] NULLABLE | For `partial` status: which services allowed |
| `blocked_service_ids` | UUID[] NULLABLE | Specific blocked services |
| `override_conflict_rules` | BOOLEAN | Admin bypass for mutual exclusivity |
| `notes` | TEXT NULLABLE | Internal admin note |
| `special_instructions` | TEXT NULLABLE | Displayed to devotees |
| `created_by` | UUID FK | — |
| `updated_by` | UUID FK | — |

---

#### `conflict_rules`

Data-driven mutual exclusivity configuration. Replaces hardcoded logic.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `rule_name` | TEXT | e.g., `kaapu_kavasam_exclusivity` |
| `service_id_a` | UUID FK | First service |
| `service_id_b` | UUID FK | Conflicting service |
| `scope` | ENUM | `same_date`, `same_session` |
| `direction` | ENUM | `bidirectional`, `a_blocks_b` |
| `is_active` | BOOLEAN | Enable/disable the rule |
| `can_admin_override` | BOOLEAN | Whether super admin can bypass |
| `notes` | TEXT | — |

---

#### `notices`

CMS-managed public notices.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `type` | ENUM | `announcement`, `homepage`, `emergency`, `banner`, `scheduled` |
| `title` | TEXT | — |
| `body` | TEXT | Full notice content |
| `priority` | INTEGER | Lower = higher priority |
| `is_active` | BOOLEAN | — |
| `published_at` | TIMESTAMPTZ NULLABLE | Schedule for future publication |
| `expires_at` | TIMESTAMPTZ NULLABLE | Auto-deactivate after this time |
| `created_by` | UUID FK | — |

---

#### `audit_logs`

Immutable audit trail for all write operations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | — |
| `actor_id` | UUID NULLABLE | User who triggered the action |
| `actor_role` | TEXT | Role at time of action |
| `action` | TEXT | e.g., `booking.created`, `slot.blocked`, `user.disabled` |
| `entity_type` | TEXT | e.g., `booking`, `service`, `notice` |
| `entity_id` | UUID NULLABLE | ID of affected entity |
| `before_state` | JSONB NULLABLE | Previous value snapshot |
| `after_state` | JSONB NULLABLE | New value snapshot |
| `ip_address` | TEXT | Client IP |
| `user_agent` | TEXT | — |
| `created_at` | TIMESTAMPTZ | Immutable timestamp |

**RLS Policy:** `audit_logs` rows can only be `INSERT`ed, never `UPDATE`d or `DELETE`d, even by service role.

---

### Entity Relationship Summary

```
users ──< bookings >── services
              │               │
          payments       slot_inventory
              │
       booking_persons

services >── conflict_rules
services >── calendar_dates (via allowed/blocked arrays)

e_undiyal_transactions >── payments

notices (independent)
audit_logs (independent — written by app, read by admins)
```

---

## 5. Authentication & Authorization Architecture

### Authentication Flow

```
Devotee (Public User)
    │
    ├── Option A: Phone OTP
    │       └── POST /auth/otp/send → Supabase Auth (SMS OTP)
    │           POST /auth/otp/verify → Returns JWT + Refresh Token
    │
    └── Option B: Email + Password
            └── POST /auth/login → Supabase Auth
                └── Returns JWT + Refresh Token

Admin User
    └── POST /auth/admin/login
            ├── Email + Password (Supabase Auth)
            ├── TOTP 2FA verification (mandatory)
            └── Returns Admin JWT with elevated claims
```

### JWT Structure

All Supabase JWTs include a custom `app_role` claim set via a Supabase Auth Hook or Database trigger on the `users` table.

```
Header: { alg: HS256, typ: JWT }
Payload:
    {
        sub: "<user_uuid>",
        email: "...",
        phone: "...",
        app_role: "devotee" | "staff" | "admin" | "super_admin",
        exp: <unix_timestamp>,
        iat: <unix_timestamp>
    }
```

FastAPI validates the JWT on every protected request using Supabase's public JWKS endpoint. The `app_role` claim is extracted and used for RBAC decisions without any additional database query.

### Role Definitions

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `devotee` | Registered temple user | Create bookings, view own bookings, donate via E-Undiyal |
| `staff` | Temple staff | View all bookings, mark attendance, view reports (read-only) |
| `admin` | Temple administrator | Manage bookings, manage calendar, manage notices, view reports |
| `super_admin` | CMS superuser | All admin capabilities + manage services, manage users, manage roles, override conflict rules, export data |

### RBAC Guard Implementation

FastAPI dependency injection is used to inject role guards into route handlers.

Every route handler declares the minimum role required via a dependency. The dependency:
1. Extracts Bearer token from `Authorization` header.
2. Verifies signature against Supabase JWKS.
3. Checks token expiry.
4. Extracts `app_role` claim.
5. Compares against the required minimum role (hierarchy enforced).
6. Raises HTTP 401 if token is invalid/expired, HTTP 403 if role is insufficient.

### Admin Two-Factor Authentication

All admin roles (`admin`, `super_admin`) require TOTP 2FA on login. The flow:

1. Admin submits email + password.
2. Supabase Auth validates credentials.
3. FastAPI middleware detects admin role.
4. FastAPI requires TOTP code submission before issuing a session token.
5. Session tokens for admins have a shorter expiry (4 hours vs 7 days for devotees).

### Row Level Security (RLS) at Database Level

RLS is enabled on all tables. Supabase RLS policies enforce data isolation at the PostgreSQL level as a second layer of defense:

| Table | Policy |
|-------|--------|
| `bookings` | Devotees see only own bookings. Admins see all. |
| `users` | Users see only own record. Admins see all. |
| `e_undiyal_transactions` | Users see own transactions. Admins see all. |
| `audit_logs` | No user access. Admin read only. Super admin read only. |
| `services` | Public read (active services). Write restricted to admin/super_admin. |
| `notices` | Public read (active, published, non-expired). Write restricted to admin. |
| `slot_inventory` | No direct public read. All reads via FastAPI service layer. |

---

## 6. Service Catalogue & Business Rules

### Complete Service List

| # | Service | Category | Session | Max Persons/Booking | Family-Based | Advance Days |
|---|---------|----------|---------|---------------------|--------------|--------------|
| 1 | Moolavar Abishegam | Abhisegam | Morning | 3 per family × 10 families | Yes | 3 |
| 2 | Ganapathy Homam | Homam | Morning | 5 | No | 5 |
| 3 | Moolavar Sandhana Kaapu | Kaapu | Morning | 5 | No | 3 |
| 4 | Moolavar Vennai Kaapu | Kaapu | Morning | 5 | No | 3 |
| 5 | Kavasam (All events) | Kavasam | All Day | 5 | No | 3 |
| 6 | Gold Chariot | Chariot | Morning / Evening | 5 | No | 3 |
| 7 | Silver Chariot | Chariot | Morning / Evening | 5 | No | 3 |
| 8 | Urchavar Thirukalyanam | Thirukalyanam | Morning | 5 | No | 3 |
| 9 | Annadhanam Prasadha Thonnai | Annadhanam | Session 1/2/3 | 5 | No | 3 |
| 10 | Annadhanam Meals | Annadhanam | Single Session | 1 | No | 3 |

> **Note:** Sahasranama Archanai and Thirupaavadai are excluded from the platform entirely as per specification corrections.

---

### Rule: Advance Booking Days

The booking date validation enforces that the requested date is at least N calendar days in the future from the request date.

| Service | Advance Days | Example |
|---------|-------------|---------|
| Ganapathy Homam | 5 | Request Monday → Earliest: Saturday |
| All other services | 3 | Request Monday → Earliest: Thursday |

The `advance_booking_days` field in the `services` table drives this validation. The FastAPI booking service calculates `min_allowed_date = today + timedelta(days=advance_booking_days)` and rejects any request where `requested_date < min_allowed_date`.

---

### Rule: Maximum Persons Per Booking

All bookings are subject to a hard limit of **5 persons per booking**, including the primary devotee. This is validated in the Pydantic request model and re-validated in the booking service before any database write.

---

### Rule: Moolavar Abishegam Family Limits

| Limit | Value |
|-------|-------|
| Maximum families per date | 10 |
| Maximum persons per family | 3 |
| Maximum total persons | 30 |

**Enforcement:**

1. On booking request, the system queries `slot_inventory` for the Moolavar Abishegam slot on the requested date.
2. The `confirmed_count` (families confirmed) is compared to `total_capacity` (10).
3. The request's `persons_per_family` is validated to be ≤ 3.
4. Both checks must pass. If either fails, booking is rejected with a descriptive error.
5. A `SELECT FOR UPDATE` lock is held on the `slot_inventory` row during the entire transaction to prevent race conditions.

---

### Rule: Kaapu and Kavasam Mutual Exclusivity

Affected services: `Moolavar Sandhana Kaapu`, `Moolavar Vennai Kaapu`, and all Kavasam events.

All these services share the `conflict_group = 'kaapu_kavasam'`.

**Enforcement Logic:**

Before creating any booking for a service in the `kaapu_kavasam` group, the booking engine:

1. Queries the `bookings` table for the requested date.
2. Filters for all `confirmed` or `pending_payment` bookings for any service where `conflict_group = 'kaapu_kavasam'`.
3. If any booking exists for the **opposite type** (e.g., attempting to book Kaapu when a Kavasam booking exists), the request is rejected with HTTP 409 and a message: `"A conflicting booking already exists for this date. Kaapu and Kavasam services cannot coexist on the same date."`

**Post-Booking Information Display:**

When a Kaapu booking is confirmed, the `post_booking_info` JSONB field in the `bookings` table is populated:

```json
{
  "morning_abishegam": "11:00 AM",
  "evening_dharisanam": "5:45 PM",
  "display_message": "Your Kaapu booking entitles you to: Morning Abishegam at 11:00 AM and Evening Dharisanam at 5:45 PM."
}
```

The `post_booking_info` data is stored at the time of booking creation based on the service configuration in the `services` table. An admin can update this information centrally via the service configuration, but existing booking records retain their snapshot at time of booking.

---

### Rule: Chariot Session Exclusivity

Only **one chariot** is permitted per session per date.

**Valid combinations for one date:**

| Morning | Evening | Valid? |
|---------|---------|--------|
| Gold | Gold | Yes |
| Gold | Silver | Yes |
| Silver | Gold | Yes |
| Silver | Silver | Yes |
| Gold | (none) | Yes |
| Gold + Silver | (any) | **No — Invalid** |
| (any) | Gold + Silver | **No — Invalid** |

**Enforcement Logic:**

Before creating a chariot booking for a given `date + session`:

1. Query `slot_inventory` for all chariot service IDs (Gold Chariot, Silver Chariot) on the same `date + session`.
2. If `confirmed_count > 0` for any chariot service on that session, the slot is at capacity (capacity for chariot-per-session = 1).
3. The `total_capacity` in `slot_inventory` for each chariot-session combination is set to `1`, making this a natural capacity constraint.

---

### Rule: Urchavar Thirukalyanam Blocks Morning Chariot

When `Urchavar Thirukalyanam` has a confirmed booking on any date:

- Morning chariot bookings (both Gold and Silver) must be blocked.
- Evening chariot rules remain configurable by admin.

**Implementation:**

This is implemented as a conflict rule in the `conflict_rules` table:

| Field | Value |
|-------|-------|
| `rule_name` | `thirukalyanam_blocks_morning_chariot` |
| `service_id_a` | Urchavar Thirukalyanam UUID |
| `service_id_b` | Gold Chariot (Morning) UUID |
| `scope` | `same_date` |
| `direction` | `a_blocks_b` |
| `is_active` | true |
| `can_admin_override` | true |

A second identical rule exists for Silver Chariot (Morning). The booking engine queries `conflict_rules` at runtime, making the entire rule set configurable by admin without code changes.

---

### Rule: Ganapathy Homam and Chariot Notice

When `Ganapathy Homam` is already confirmed on a date:

- Kaapu and Kavasam bookings are still allowed (no conflict rule between them).
- Chariot bookings are **not automatically blocked** but require a notice.

**Implementation:**

A special service configuration flag `requires_admin_approval = true` is set on Chariot services specifically for dates where Ganapathy Homam exists.

**Conflict Check Flow for Chariot + Ganapathy Homam:**

1. Booking request received for Chariot on date D.
2. Booking engine queries for confirmed Ganapathy Homam bookings on date D.
3. If Ganapathy Homam exists: `requires_admin_approval` is forced to `true` for this booking, regardless of service configuration.
4. Booking is created with `status = pending_payment`, but after payment, status becomes `pending_approval` instead of `confirmed`.
5. Admin receives a notification to manually confirm chariot availability.
6. The API response includes: `{ "notice": "Please contact temple administration and confirm availability before proceeding with Chariot booking.", "requires_approval": true }`.

**Admin Override Mechanism:**

- Admin views pending_approval chariot bookings via CMS.
- Admin confirms or rejects with a reason.
- On confirmation: `status → confirmed`, slot count decremented, devotee notified.
- On rejection: `status → rejected`, payment refund initiated, devotee notified.

---

### Rule: Annadhanam Prasadha Thonnai

| Setting | Rule |
|---------|-------|
| Sessions | Session 1, Session 2, Session 3 |
| Max capacity per session | Admin-configurable via `slot_inventory.total_capacity` |
| Allocation method | First paid, first confirmed |
| Duplicate booking | A user who has already paid for a session cannot book again for the same session on the same date |

**Enforcement Logic:**

1. On booking request, check `slot_inventory` for the session. If `confirmed_count >= total_capacity`, reject with HTTP 409 (`"This session is fully booked."`).
2. Capacity check is done **before** payment initiation.
3. A payment hold (`pending_count++`) is applied when payment is initiated.
4. After payment success webhook: `confirmed_count++`, `pending_count--`.
5. If payment fails/times out: `pending_count--` is reversed via a background cleanup job.
6. **Duplicate booking check:** Before payment initiation, query `bookings` table for the same `user_id + service_id + date + session` where `status IN ('confirmed', 'pending_payment')`. If found, reject with HTTP 409 (`"You have already booked this session."`).

---

### Rule: Annadhanam Meals

| Setting | Rule |
|---------|-------|
| Sessions | Single session only |
| Persons per booking | 1 (exactly one participant) |
| Capacity | Admin-configurable |
| Duplicate prevention | Same user cannot book Annadhanam Meals twice on same date |

The `max_persons_per_booking` for Annadhanam Meals is set to `1` in the `services` table, and the booking engine rejects any request where `num_persons != 1`.

---

## 7. Booking Engine Architecture

### Booking State Machine

```
[Draft / No State]
        │
        ▼
[pending_payment] ──── Payment Timeout (15 min) ──→ [cancelled]
        │
        ▼ (Payment Success Webhook)
        │
        ├── requires_approval = false ──→ [confirmed]
        │
        └── requires_approval = true  ──→ [pending_approval]
                                              │
                              ┌───────────────┴───────────────┐
                              ▼                               ▼
                         [confirmed]                    [rejected]
                              │                               │
                              ▼                               ▼
                         [cancelled]                    [refunded]
                              │
                              ▼
                         [refunded]
```

### Booking Creation Sequence

The booking engine executes all steps within a **single database transaction**:

```
Step 1: Validate Request
        ├── Pydantic model validation (types, required fields)
        ├── Date within allowed range (advance booking days)
        ├── Person count ≤ service max_persons_per_booking
        └── For Moolavar Abishegam: family count ≤ 10, persons_per_family ≤ 3

Step 2: Calendar Check
        └── Query calendar_dates for requested date
            ├── status = 'blocked' → Reject: "Bookings not available on this date"
            ├── status = 'partial' → Check if service_id in allowed_service_ids
            └── status = 'open' → Proceed

Step 3: Conflict Rule Check (within transaction)
        └── Query conflict_rules for the service_id
            └── For each active conflict rule, check if conflicting service
                has confirmed/pending bookings on same date/session
                → If conflict found: Reject with HTTP 409

Step 4: Capacity Check (with row lock)
        └── SELECT * FROM slot_inventory
            WHERE service_id = ? AND date = ? AND session = ?
            FOR UPDATE
            ├── Row not found → Create with defaults and lock
            └── Row found:
                ├── is_blocked = true → Reject
                └── confirmed_count + pending_count >= total_capacity → Reject: "Slot full"

Step 5: Duplicate Check
        └── Query bookings for same user + service + date + session
            WHERE status IN ('confirmed', 'pending_payment')
            → If found: Reject with HTTP 409

Step 6: Ganapathy Homam Special Check (for Chariot only)
        └── If service.category = 'chariot':
            Check for Ganapathy Homam on same date
            → If exists: Set requires_approval = true

Step 7: Create Booking Record
        └── INSERT into bookings with status = 'pending_payment'
            INSERT into booking_persons

Step 8: Increment Pending Count
        └── UPDATE slot_inventory SET pending_count = pending_count + 1

Step 9: Initiate Payment Order
        └── Call payment gateway API to create order
            Store gateway_order_id in payments table

Step 10: Write Audit Log (background task, outside transaction)
        └── Log action: booking.created
```

### Payment Completion Sequence

```
Step 1: Receive webhook from payment gateway
Step 2: Verify webhook signature (HMAC)
Step 3: Begin transaction
Step 4: Lock booking row (SELECT FOR UPDATE)
Step 5: Verify booking status = 'pending_payment'
Step 6: Verify payment amount matches booking amount
Step 7: Lock slot_inventory row (SELECT FOR UPDATE)
Step 8: Re-verify capacity (final check): confirmed_count + 1 <= total_capacity
        → If capacity exceeded (edge case): Reject, initiate refund
Step 9: Update booking status:
        → requires_approval = false: status → 'confirmed'
        → requires_approval = true: status → 'pending_approval'
Step 10: UPDATE slot_inventory:
        confirmed_count += 1
        pending_count -= 1
Step 11: Update payment record: status = 'success'
Step 12: Commit transaction
Step 13: Background tasks:
        ├── Generate PDF receipt → Upload to Supabase Storage
        ├── Send confirmation SMS/Email
        └── Write audit log
```

---

## 8. E-Undiyal Architecture

E-Undiyal is a **donation mechanism**, not a booking. It has no slot inventory, no conflict rules, no advance booking requirements, and no capacity limits.

### Architecture Separation

| Aspect | Bookings | E-Undiyal |
|--------|----------|-----------|
| Table | `bookings` | `e_undiyal_transactions` |
| Routing | `/api/v1/bookings/*` | `/api/v1/e-undiyal/*` |
| Slot deduction | Yes | No |
| Conflict check | Yes | No |
| Capacity limit | Yes | No |
| Receipt type | Booking confirmation | Donation receipt |
| Tax benefit | No | 80G eligible |

### E-Undiyal Flow

```
1. User (logged in or guest) submits donation intent
   POST /api/v1/e-undiyal/initiate
   { donor_name, donor_phone, donor_email, amount_paise }

2. FastAPI creates e_undiyal_transactions record (status: initiated)
   Creates payment gateway order

3. User completes payment via gateway

4. Payment gateway sends webhook
   POST /api/v1/webhooks/payment (differentiated by order type metadata)

5. FastAPI updates e_undiyal_transactions status → 'success'
   Generates 80G-eligible donation receipt PDF
   Uploads to Supabase Storage
   Sends receipt to donor via email/SMS

6. Response includes receipt_url
```

### E-Undiyal Admin Features

- View all donations (searchable, filterable by date/amount)
- Export donation reports
- No approve/reject flow (auto-confirmed on payment)

---

## 9. Calendar Management System

### Admin Calendar Capabilities

The calendar management system allows super admins and admins to configure booking availability at a per-date level, overriding default service rules.

| Admin Action | Database Effect |
|-------------|-----------------|
| Block entire date | `calendar_dates.status = 'blocked'` |
| Open date for all services | `calendar_dates.status = 'open'` (or no row = default open) |
| Partially allow date | `calendar_dates.status = 'partial'`, `allowed_service_ids = [...]` |
| Block specific services on a date | `calendar_dates.blocked_service_ids = [...]` |
| Override conflict rules | `calendar_dates.override_conflict_rules = true` |
| Add public note | `calendar_dates.special_instructions = "..."` |
| Configure multiple dates at once | Batch INSERT/UPSERT into `calendar_dates` |
| Configure date ranges | API accepts `{ start_date, end_date, config }` and expands to individual rows |
| Configure future years | Standard date columns support any year. Admin can pre-configure 2026, 2027, etc. |

### Calendar Query Logic in Booking Engine

```
GET /api/v1/calendar/availability?service_id=X&date=Y

1. Query calendar_dates WHERE date = Y
   → No row found: Date is open (apply default service rules)
   → Row found with status = 'blocked': Return availability = false

2. If status = 'partial':
   → Check if service_id X in allowed_service_ids
   → If not found: Return availability = false
   → If found: Proceed to standard capacity/conflict check

3. If calendar_dates.override_conflict_rules = true:
   → Skip conflict_rules check in booking engine

4. Return { available: bool, capacity_remaining: int, special_instructions: string }
```

### Calendar API Endpoints (Admin)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/calendar` | View calendar month overview |
| GET | `/admin/calendar/{date}` | View specific date config |
| PUT | `/admin/calendar/{date}` | Configure single date |
| POST | `/admin/calendar/bulk` | Configure multiple dates or date range |
| DELETE | `/admin/calendar/{date}` | Reset date to default (open) |

---

## 10. Payment Integration Layer

### Supported Gateways

The architecture is designed to be gateway-agnostic. The recommended primary gateway is **Razorpay** (widely used in India, supports UPI, cards, net banking). PayU is the recommended fallback.

### Payment Flow Architecture

```
Frontend (separate project)
    │
    ├── Step 1: Call FastAPI to create payment order
    │   POST /api/v1/payments/create-order
    │   { booking_id }
    │   → Returns: { gateway_order_id, amount, currency }
    │
    └── Step 2: Open gateway payment modal with order details
        │
        ▼ (User completes payment in gateway UI)
        │
        ├── Gateway sends WEBHOOK to FastAPI
        │   POST /api/v1/webhooks/payment/razorpay
        │   (Signature verified → booking confirmed)
        │
        └── Gateway redirects user to frontend
            Frontend calls: GET /api/v1/bookings/{id}/status
            → Returns current booking status (confirmed / pending_approval / failed)
```

### Webhook Security

All payment webhooks are verified via HMAC-SHA256 signature validation before any processing occurs. The webhook secret is stored in environment variables, never in code or database.

Webhook processing is idempotent: If the same webhook is received twice (gateway retries), the second processing is a no-op (booking is already confirmed).

### Refund Architecture

```
Admin initiates refund via CMS
    │
    ▼
FastAPI → Payment Gateway Refund API
    │
    ▼
Gateway sends refund webhook
    │
    ▼
FastAPI updates:
    payments.status = 'refunded'
    payments.refund_id = gateway_refund_id
    bookings.status = 'refunded'
    slot_inventory.confirmed_count -= 1  (slot released)
    │
    ▼
Audit log written
Devotee notified via SMS/Email
```

---

## 11. CMS / Super Admin Portal Architecture

### CMS API Structure

The CMS is a separate FastAPI router prefix `/admin/*` protected by admin/super_admin role guards.

The CMS uses the same FastAPI application — no separate backend process. Route-level RBAC guards enforce separation.

### CMS Modules

#### Service Management

| Operation | Endpoint | Role Required |
|-----------|----------|---------------|
| List services | GET `/admin/services` | admin |
| Get service detail | GET `/admin/services/{id}` | admin |
| Create service | POST `/admin/services` | super_admin |
| Update service | PUT `/admin/services/{id}` | super_admin |
| Enable/Disable service | PATCH `/admin/services/{id}/status` | admin |
| Update pricing | PATCH `/admin/services/{id}/price` | super_admin |
| Update capacity | PATCH `/admin/services/{id}/capacity` | super_admin |
| Update advance days | PATCH `/admin/services/{id}/advance-days` | super_admin |

#### Booking Management

| Operation | Endpoint | Role Required |
|-----------|----------|---------------|
| List bookings (with filters) | GET `/admin/bookings` | admin |
| Get booking detail | GET `/admin/bookings/{id}` | admin |
| Approve booking | POST `/admin/bookings/{id}/approve` | admin |
| Reject booking | POST `/admin/bookings/{id}/reject` | admin |
| Cancel booking | POST `/admin/bookings/{id}/cancel` | admin |
| Initiate refund | POST `/admin/bookings/{id}/refund` | admin |
| View conflicts | GET `/admin/bookings/conflicts` | admin |
| Search bookings | GET `/admin/bookings?q=...&date=...&service=...&status=...` | admin |
| Export bookings | GET `/admin/bookings/export?format=csv` | admin |

#### User Management

| Operation | Endpoint | Role Required |
|-----------|----------|---------------|
| List users | GET `/admin/users` | admin |
| Get user detail + booking history | GET `/admin/users/{id}` | admin |
| Update user profile | PUT `/admin/users/{id}` | super_admin |
| Disable account | PATCH `/admin/users/{id}/disable` | super_admin |
| Enable account | PATCH `/admin/users/{id}/enable` | super_admin |
| Change user role | PATCH `/admin/users/{id}/role` | super_admin |

#### Conflict Rule Management

| Operation | Endpoint | Role Required |
|-----------|----------|---------------|
| List conflict rules | GET `/admin/conflict-rules` | super_admin |
| Create rule | POST `/admin/conflict-rules` | super_admin |
| Update rule | PUT `/admin/conflict-rules/{id}` | super_admin |
| Enable/Disable rule | PATCH `/admin/conflict-rules/{id}/status` | super_admin |

#### Slot Inventory Management

| Operation | Endpoint | Role Required |
|-----------|----------|---------------|
| View inventory for date | GET `/admin/inventory?date=...` | admin |
| Adjust capacity | PATCH `/admin/inventory/{service_id}/{date}/capacity` | super_admin |
| Block slot | PATCH `/admin/inventory/{service_id}/{date}/block` | admin |
| Unblock slot | PATCH `/admin/inventory/{service_id}/{date}/unblock` | admin |

---

## 12. Notice Management System

### Notice Types and Behavior

| Type | Display Location | Auto-expire | Priority |
|------|-----------------|-------------|----------|
| `emergency` | Full-screen overlay on website | Optional | 1 (highest) |
| `banner` | Top banner on all pages | Yes | 2 |
| `homepage` | Homepage notice section | Yes | 3 |
| `announcement` | Announcements page | Yes | 4 |
| `scheduled` | Published at future `published_at` time | Yes | 5 |

### Notice Lifecycle

```
Draft (not yet active) → Active (is_active = true, published_at <= now) → Expired (expires_at < now)
```

A background job runs every 5 minutes to:
1. Activate notices where `published_at <= now AND is_active = false`.
2. Deactivate notices where `expires_at < now AND is_active = true`.
3. Write audit log for each status change.

### CMS-to-Website Synchronization

The public website does not read from the database directly. All notice data flows through the FastAPI API:

```
CMS Admin creates/updates notice
    → FastAPI writes to notices table
    → FastAPI invalidates CDN cache for /api/v1/notices endpoint

Website Frontend
    → Calls GET /api/v1/notices?type=banner&active=true
    → FastAPI queries notices WHERE is_active = true AND published_at <= now
      AND (expires_at IS NULL OR expires_at > now) ORDER BY priority
    → Returns JSON to frontend

Cache Strategy:
    → Active notices cached at CDN edge (Cloudflare) with short TTL (60 seconds)
    → Cache invalidated on any notice write operation via Cache-Control headers or purge API
```

### Notice API (Public)

| Endpoint | Description |
|----------|-------------|
| GET `/api/v1/notices` | All active notices (filtered by type) |
| GET `/api/v1/notices/emergency` | Emergency notices only |
| GET `/api/v1/notices/banner` | Banner notices only |

### Notice API (Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/notices` | List all notices |
| POST | `/admin/notices` | Create notice |
| PUT | `/admin/notices/{id}` | Update notice |
| PATCH | `/admin/notices/{id}/activate` | Immediately activate |
| PATCH | `/admin/notices/{id}/deactivate` | Deactivate |
| DELETE | `/admin/notices/{id}` | Delete notice (soft delete) |

---

## 13. Reporting & Analytics System

### Report Categories

#### Daily Reports

| Report | Key Metrics |
|--------|-------------|
| Daily Booking Summary | Total bookings, confirmations, cancellations, rejections by service |
| Daily Revenue | Total collected, pending, refunded in INR |
| Daily Capacity Utilization | Booked vs available slots per service per session |
| Daily E-Undiyal Summary | Total donations, total amount, donor count |
| Daily Conflict Events | Number of conflict rejections, type of conflicts triggered |
| Daily Admin Activity | CMS logins, configuration changes, approvals/rejections |

#### Weekly Reports

| Report | Key Metrics |
|--------|-------------|
| Weekly Booking Trend | Day-over-day booking volume chart data |
| Weekly Revenue Trend | Revenue by service category |
| Weekly Capacity Summary | Average utilization per service per session |
| Weekly Cancellation Report | Cancellations by reason, by service, refund amounts |

#### Monthly Reports

| Report | Key Metrics |
|--------|-------------|
| Monthly Revenue Report | Gross revenue, net revenue (after refunds), by service, by payment method |
| Monthly Service Performance | Most booked services, least booked, occupancy rates |
| Monthly User Report | New registrations, active users, user retention |
| Monthly Booking Source | OTP vs email login breakdown |
| Monthly Conflict Report | Conflict rules triggered, admin overrides used |

#### Yearly Reports

| Report | Key Metrics |
|--------|-------------|
| Annual Revenue Summary | Month-by-month revenue, YoY comparison |
| Annual Service Summary | Service utilization trends |
| Annual Donation Summary | E-Undiyal totals, donor retention |
| Annual User Growth | User base growth |

#### Custom Reports

Admin can configure:
- Date range
- Service filter
- Status filter
- User segment
- Payment method filter
- Export format (CSV, PDF)

#### Specific Report Types

| Report | Description |
|--------|-------------|
| Blocked Slot Report | All slots blocked per date/service, reason |
| Occupancy Report | Utilization percentage per service per date |
| Pending Approval Report | Bookings in `pending_approval` state |
| Refund Tracking Report | All refunds, amounts, reasons, gateway refund IDs |
| Audit Report | Admin actions log, exportable |
| Payment Failure Report | Failed payment attempts by date/service |
| Duplicate Attempt Report | Prevented duplicate booking attempts |

### KPI Dashboard

| KPI | Calculation |
|-----|-------------|
| Total Revenue (MTD) | SUM of confirmed payment amounts for current month |
| Occupancy Rate | confirmed_count / total_capacity × 100 per service |
| Booking Conversion Rate | confirmed / (confirmed + failed payments) × 100 |
| Cancellation Rate | cancelled / total_bookings × 100 |
| Average Booking Value | Total revenue / total confirmed bookings |
| E-Undiyal Conversion | Completed donations / initiated donations × 100 |
| Active Users (30-day) | Users with at least one booking in last 30 days |
| Conflict Block Rate | Conflict rejections / total booking attempts × 100 |

### Forecasting

The reporting system stores historical daily metrics in a `metrics_snapshots` table. This enables:
- Identifying peak booking days by service
- Seasonal demand patterns
- Capacity planning recommendations (e.g., "Ganapathy Homam fills 5 days in advance 80% of the time")

### Report Export

Reports are generated as CSV or PDF and:
- Uploaded to Supabase Storage with a signed URL.
- Signed URL is returned to admin with 1-hour expiry.
- Large reports are generated as background jobs; admin receives notification when ready.

### Reporting API (Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/reports/daily` | Daily summary |
| GET | `/admin/reports/weekly` | Weekly summary |
| GET | `/admin/reports/monthly` | Monthly summary |
| GET | `/admin/reports/yearly` | Yearly summary |
| POST | `/admin/reports/custom` | Custom date range + filters |
| GET | `/admin/reports/export/{report_id}` | Download generated report |
| GET | `/admin/dashboard/kpis` | Real-time KPI data |
| GET | `/admin/dashboard/charts` | Chart data (time series) |

---

## 14. User Management System

### User Profile

Each user record in the `users` table is extended from the Supabase Auth user. The profile contains:

- Full name, phone (verified), email
- Role assignment
- Account status (active/disabled)
- Registration date
- Last login timestamp

### User Booking History

Admin can retrieve complete booking history for any user:
- All bookings across all services
- Status, date, amount paid, refund status
- E-Undiyal donations

### Admin Permission Matrix

| Action | staff | admin | super_admin |
|--------|-------|-------|-------------|
| View user list | Yes | Yes | Yes |
| View user detail | Yes | Yes | Yes |
| View booking history | Yes | Yes | Yes |
| Edit user profile | No | No | Yes |
| Disable account | No | No | Yes |
| Enable account | No | No | Yes |
| Change role | No | No | Yes (cannot escalate above own role) |
| Export user data | No | Yes | Yes |

### Account Disable Flow

When a super_admin disables an account:
1. `users.is_active` is set to `false`.
2. Supabase Auth is called via Admin API to ban the user (prevents future logins).
3. Existing active sessions are invalidated (Supabase Auth ban invalidates JWTs).
4. Audit log is written with actor, reason, and timestamp.
5. User's pending bookings are not automatically cancelled (admin decides separately).

---

## 15. FastAPI Application Architecture

### Application Structure

```
app/
├── main.py                    # Application entry point, middleware setup
├── config.py                  # Settings via Pydantic BaseSettings
├── database.py                # Supabase async client setup
│
├── routers/
│   ├── public/
│   │   ├── services.py        # GET /api/v1/services
│   │   ├── availability.py    # GET /api/v1/availability
│   │   ├── notices.py         # GET /api/v1/notices
│   │   └── e_undiyal.py       # POST /api/v1/e-undiyal/*
│   │
│   ├── auth/
│   │   ├── otp.py             # OTP send/verify
│   │   └── login.py           # Email/password login, 2FA
│   │
│   ├── bookings/
│   │   ├── create.py          # POST /api/v1/bookings
│   │   ├── status.py          # GET /api/v1/bookings/{id}
│   │   └── list.py            # GET /api/v1/bookings (user's own)
│   │
│   ├── payments/
│   │   ├── create_order.py    # POST /api/v1/payments/create-order
│   │   └── webhooks.py        # POST /api/v1/webhooks/payment/*
│   │
│   └── admin/
│       ├── services.py
│       ├── bookings.py
│       ├── users.py
│       ├── calendar.py
│       ├── inventory.py
│       ├── notices.py
│       ├── reports.py
│       ├── dashboard.py
│       └── conflict_rules.py
│
├── services/
│   ├── booking_engine.py      # Core booking logic
│   ├── conflict_checker.py    # Conflict rule evaluation
│   ├── calendar_service.py    # Calendar date checks
│   ├── payment_service.py     # Payment gateway abstraction
│   ├── receipt_service.py     # PDF generation
│   ├── notification_service.py # SMS/Email notifications
│   ├── audit_service.py       # Audit log writes
│   └── report_service.py      # Report generation
│
├── models/
│   ├── db/                    # Database ORM models (SQLModel / asyncpg)
│   └── schemas/               # Pydantic request/response schemas
│
├── dependencies/
│   ├── auth.py                # JWT verification, role guards
│   └── db.py                  # Database session injection
│
├── middleware/
│   ├── rate_limit.py          # Per-IP, per-user rate limiting
│   ├── request_logging.py     # Structured request/response logging
│   └── cors.py                # CORS configuration
│
└── background/
    ├── slot_cleanup.py        # Expired pending_payment cleanup
    ├── notice_scheduler.py    # Notice publish/expire automation
    └── report_generator.py    # Async report generation
```

### API Versioning

All public and booking endpoints are versioned under `/api/v1/`. Admin endpoints are under `/admin/`. This allows future API versions (`v2`) to be introduced without breaking existing frontend integrations.

### Caching Strategy

| Data | Cache Location | TTL | Invalidation |
|------|----------------|-----|--------------|
| Active notices | Cloudflare CDN edge | 60 seconds | On write via Cache-Control |
| Service catalogue | In-process cache (Starlette) | 5 minutes | On service update |
| Calendar date config | In-process cache | 5 minutes | On calendar update |
| Slot availability | **Not cached** | — | Always fresh (atomically locked) |
| Report data (large) | Supabase Storage | Until regenerated | Manual by admin |

Slot availability is **never cached** due to the zero-overbooking requirement.

### Background Job Architecture

Background jobs are managed by **APScheduler** (integrated into FastAPI):

| Job | Schedule | Description |
|-----|----------|-------------|
| `slot_cleanup` | Every 5 minutes | Find `pending_payment` bookings older than 15 minutes, cancel them, release `pending_count` |
| `notice_scheduler` | Every 5 minutes | Activate/expire notices |
| `metrics_snapshot` | Daily at 00:05 | Write daily metrics to `metrics_snapshots` |
| `report_cleanup` | Weekly | Delete expired report files from Supabase Storage |

### How CMS Uses APIs

The CMS (admin portal, a separate frontend project) interacts exclusively with FastAPI admin endpoints:
- Authentication via admin JWT with TOTP.
- All write operations go through FastAPI (never direct Supabase SDK calls from frontend).
- FastAPI enforces all business rules on admin operations (e.g., blocking a date still goes through the calendar service).

### How the Public Website Uses APIs

The public website (separate frontend project):
- Reads service catalogue via GET `/api/v1/services`.
- Checks availability via GET `/api/v1/availability`.
- Authenticates devotees via POST `/api/v1/auth/*`.
- Creates bookings via POST `/api/v1/bookings`.
- Initiates payments via POST `/api/v1/payments/create-order`.
- Reads notices via GET `/api/v1/notices`.

---

## 16. Supabase Architecture

### Database Connection

FastAPI connects to Supabase PostgreSQL using the **connection pooling URL (PgBouncer on port 6543)** with `asyncpg` as the async driver. The service role key is used for all FastAPI database operations (bypasses RLS — FastAPI enforces its own authorization layer).

The frontend and CMS **never** connect directly to Supabase with the service role key. Only FastAPI holds the service role key.

### Environment Separation

| Environment | Supabase Project | Purpose |
|-------------|-----------------|---------|
| Development | `smvd-dev` | Local development and testing |
| Staging | `smvd-staging` | QA, UAT, integration testing |
| Production | `smvd-prod` | Live system |

Each environment has:
- Separate Supabase project with separate credentials.
- Separate payment gateway test/live keys.
- Separate email/SMS credentials.

### Migration Strategy

Database schema changes are managed via:
- **Supabase CLI** for local development (generates migration files).
- **Alembic** as the migration tool within FastAPI for tracking schema versions.
- Migrations are version-controlled in the repository.
- CI/CD pipeline runs migrations on staging before production deployment.
- Each migration includes an explicit rollback script.

### Supabase Storage Architecture

| Bucket | Access | Contents |
|--------|--------|----------|
| `booking-receipts` | Private (signed URL only) | Booking confirmation PDFs |
| `donation-receipts` | Private (signed URL only) | E-Undiyal donation receipts |
| `reports` | Private (admin signed URL) | Generated CSV/PDF reports |
| `service-images` | Public | Temple service images for website |
| `notice-media` | Public | Notice banner images |

All private bucket access is via signed URLs with short expiry (1 hour for user receipts, 30 minutes for admin reports).

### Backup Strategy

- Supabase Pro provides automatic daily backups with 7-day retention.
- Production environment uses Supabase Enterprise for point-in-time recovery (PITR) with up to 30-day recovery window.
- Weekly manual backup exports (pg_dump) are stored in a separate cloud storage (AWS S3 or Cloudflare R2) with 90-day retention.
- Backup restoration is tested on the staging environment monthly.

---

## 17. Security Architecture

### Authentication Security

| Control | Implementation |
|---------|----------------|
| Password hashing | Supabase Auth handles bcrypt hashing |
| JWT secret rotation | Supabase manages JWKS rotation; FastAPI fetches current keys |
| Token expiry | Devotees: 7 days. Admins: 4 hours. |
| Refresh token rotation | Enabled in Supabase Auth |
| 2FA (Admin) | TOTP (Google Authenticator compatible) — mandatory |
| OTP brute force | Supabase Auth rate limits OTP attempts; FastAPI adds additional IP-based limiting |
| Session invalidation | Supabase Auth ban instantly invalidates JWTs |

### Authorization & RBAC

| Control | Implementation |
|---------|----------------|
| Role enforcement | FastAPI dependency injection on every protected route |
| Horizontal privilege escalation | Booking queries always filter by `user_id = current_user.id` for non-admin roles |
| Admin route isolation | Admin router prefix requires `admin` or `super_admin` role at router level |
| Role escalation prevention | Super admins cannot assign roles higher than their own |
| RLS as backup | Supabase RLS provides second-layer enforcement even if FastAPI auth is bypassed |

### Rate Limiting

| Endpoint Category | Limit |
|-------------------|-------|
| OTP request | 3 per phone number per 10 minutes |
| Login attempts | 5 per IP per 5 minutes |
| Booking creation | 10 per user per hour |
| Payment order creation | 5 per user per 30 minutes |
| Public API (notices, services) | 100 per IP per minute |
| Admin API | 200 per admin user per minute |
| Webhook endpoint | Unlimited (verified by signature, not rate-limited to ensure reliability) |

Rate limiting is implemented via `slowapi` (FastAPI) with Redis as the backend store for distributed rate limit state.

### Input Validation

- All request bodies are validated by Pydantic models before reaching any service layer.
- String fields have `max_length` constraints.
- Numeric fields have `ge` / `le` (min/max) constraints.
- Date fields are validated for format and range.
- Phone numbers are validated against E.164 format.
- Amount fields are validated to be positive integers (paise).
- SQL injection is prevented by parameterized queries via asyncpg (no string interpolation in queries).
- XSS is mitigated by returning only JSON responses (no HTML rendering in FastAPI); content is sanitized on frontend.

### API Security

| Control | Implementation |
|---------|----------------|
| HTTPS only | TLS 1.2+ enforced at Nginx; HTTP → HTTPS redirect |
| CORS | Strict allowlist of frontend/admin domains only |
| CSRF | Not applicable for API-only backend (no cookie-based sessions); JWTs in Authorization header |
| Security headers | `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` set by Nginx |
| Content-Type enforcement | FastAPI rejects non-JSON content types on JSON endpoints |
| Response stripping | No internal IDs, stack traces, or system info returned in error responses |

### Webhook Security

Payment gateway webhooks are verified using HMAC-SHA256 signature validation:
1. Webhook payload received.
2. Signature extracted from `X-Razorpay-Signature` header.
3. FastAPI computes HMAC-SHA256 of raw request body using the webhook secret.
4. If signatures don't match: request rejected with HTTP 400, incident logged.
5. Processing continues only after signature verification passes.

### DDoS and Network Security

| Layer | Control |
|-------|---------|
| CDN | Cloudflare DDoS protection (L3/L4) |
| Application | Nginx connection limits and request rate limiting |
| Supabase | Supabase network isolation (no direct internet access to PostgreSQL) |
| IP allowlisting | Admin portal only accessible from allowlisted IPs (configurable) |

### Secrets Management

| Secret | Storage |
|--------|---------|
| Supabase service role key | Environment variable (never in code) |
| Payment gateway API keys | Environment variable |
| Payment webhook secrets | Environment variable |
| JWT secret (Supabase JWKS) | Fetched from Supabase JWKS URL at startup |
| 2FA seed (admin TOTP) | Supabase Auth (encrypted) |
| Database URL | Environment variable |
| SMS gateway API key | Environment variable |

Environment variables are managed via `.env` files locally and via the hosting platform's secrets manager (e.g., Railway variables, AWS Secrets Manager) in production. No secrets are committed to version control. `.env` is in `.gitignore`.

### Audit Logging

The `audit_logs` table is append-only. The database user used by FastAPI has `INSERT` privilege on `audit_logs` but **no** `UPDATE` or `DELETE` privilege. This is enforced at the PostgreSQL GRANT level.

Every sensitive operation writes an audit log entry:
- User registration / profile change
- Booking creation, approval, rejection, cancellation
- Payment initiation, success, failure, refund
- Calendar date configuration changes
- Service configuration changes
- Slot inventory changes
- Notice creation, modification, deletion
- Admin login/logout
- Role assignment changes
- User enable/disable

Audit logs are retained for a minimum of 2 years. Logs older than 2 years are archived to Supabase Storage (cold storage).

### Booking Fraud Prevention

| Threat | Control |
|--------|---------|
| Duplicate booking | Duplicate check query in booking engine before payment initiation |
| Slot manipulation | All slot operations use `SELECT FOR UPDATE` atomic transactions |
| Price manipulation | Frontend sends booking intent only; price is calculated server-side from `services.price_paise` |
| Amount tampering | Payment webhook validates that received amount matches expected amount |
| Fake payment webhook | HMAC signature verification on all webhooks |
| Session reuse | Short admin token expiry; Supabase refresh token rotation |

### Security Testing Plan

| Test Type | Method |
|-----------|--------|
| Authentication bypass testing | Attempt to access protected routes without valid JWT |
| Role escalation testing | Attempt to call super_admin endpoints with admin token |
| SQL injection testing | Automated scanning via SQLMap on all input fields |
| OWASP Top 10 coverage | ZAP (OWASP ZAP) automated scan |
| Webhook forgery testing | Send webhooks with invalid signatures and verify rejection |
| Rate limit testing | Automated scripts to verify limits are enforced |
| Load testing | k6 or Locust to simulate concurrent booking attempts and verify no overbooking |
| Penetration testing | Recommended: External security firm quarterly |

### Security Checklist

- [ ] All environment variables set; no secrets in codebase
- [ ] RLS enabled on all Supabase tables
- [ ] Audit log table is append-only (GRANT verified)
- [ ] Admin 2FA tested and mandatory
- [ ] Payment webhook signatures validated
- [ ] CORS allowlist is exact (no wildcards)
- [ ] Rate limiting verified on OTP and login endpoints
- [ ] All admin routes return 403 to non-admin tokens
- [ ] All booking routes return 403 to unauthenticated requests
- [ ] No internal error messages exposed to clients
- [ ] HTTPS enforced (HTTP → HTTPS redirect in Nginx)
- [ ] Duplicate booking prevention tested with concurrent requests
- [ ] Zero-overbooking verified via load test (concurrent bookings)

---

## 18. Deployment Architecture

### Recommended Hosting Architecture

```
                    ┌───────────────────┐
                    │   Cloudflare      │
                    │  (DNS + DDoS +    │
                    │   CDN + WAF)      │
                    └─────────┬─────────┘
                              │
              ┌───────────────▼───────────────┐
              │    Railway / Render / Fly.io   │
              │                               │
              │  ┌──────────────────────────┐ │
              │  │   FastAPI (Uvicorn +     │ │
              │  │   Gunicorn)              │ │
              │  │   2–4 worker processes   │ │
              │  └──────────────────────────┘ │
              │  ┌──────────────────────────┐ │
              │  │   Redis (for rate limit  │ │
              │  │   + background jobs)     │ │
              │  └──────────────────────────┘ │
              └───────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │          Supabase             │
              │  (PostgreSQL + Auth + Storage) │
              └───────────────────────────────┘
```

### Hosting Recommendation

**Primary recommendation: Railway.app**

| Reason | Detail |
|--------|--------|
| Simplicity | Git-push deployment, environment variables management, integrated logs |
| Performance | Dockerized containers with automatic scaling |
| Cost | Predictable pricing (~$20–50/month for the API tier) |
| Region | Supports deployments close to Supabase region |
| Redis | Built-in Redis add-on |

**Alternative: Render.com** — Similar capabilities, slightly different pricing model.

**Alternative: AWS ECS (Fargate)** — For higher scale or enterprise requirements. More complex setup but maximum control.

### Domain and SSL Setup

| Domain | Purpose |
|--------|---------|
| `api.srimanakula.com` | FastAPI backend API |
| `admin.srimanakula.com` | CMS admin portal (separate frontend) |
| `srimanakula.com` | Public website (separate frontend) |

- Cloudflare manages DNS for all domains.
- Cloudflare provides automatic SSL (TLS 1.2+).
- Origin certificates are used between Cloudflare and the hosting provider.

### CI/CD Pipeline (GitHub Actions)

```
Push to main branch (production) or staging branch
    │
    ▼
GitHub Actions Workflow
    ├── Step 1: Run tests (pytest)
    ├── Step 2: Run security scan (Bandit for Python)
    ├── Step 3: Build Docker image
    ├── Step 4: Run database migrations on target environment
    ├── Step 5: Deploy to Railway (rolling deployment)
    ├── Step 6: Health check (GET /api/v1/health)
    └── Step 7: Notify team (Slack/email)

On failure: Pipeline stops, previous version remains active (no downtime)
```

### Rollback Strategy

1. Every deployment is tagged with a Git commit SHA.
2. Railway maintains the previous deployment image.
3. Rollback: Trigger Railway re-deploy of the previous image (< 2 minutes).
4. Database rollback: Alembic `downgrade` command applied manually (for schema changes).
5. All migrations are written to be reversible.

### Scaling Strategy

| Trigger | Action |
|---------|--------|
| CPU > 70% for 5 minutes | Scale API instances (Railway auto-scale) |
| Memory > 80% | Scale memory tier |
| Database connections > 80% of pool | Increase PgBouncer pool size or upgrade Supabase tier |
| Redis memory > 80% | Upgrade Redis tier |

### Cost Estimation (Monthly)

| Component | Estimated Cost |
|-----------|---------------|
| Railway (API) | $20–60 |
| Supabase Pro (Production) | $25 |
| Cloudflare Pro | $20 |
| Redis (Railway add-on) | $10–20 |
| SMS Gateway (per OTP) | ₹0.1–0.5 per OTP |
| Payment Gateway | Razorpay: 2% per transaction |
| Email Service (Postmark/Resend) | $10–20 |
| **Total (excluding variable)** | **~$85–125/month** |

---

## 19. Testing Strategy

### Local Development Setup

```
Requirements:
- Python 3.11+
- Docker (for local Redis)
- Supabase CLI (for local database)
- Postman or Bruno API client

Steps:
1. Clone repository
2. Copy .env.example to .env, fill in Supabase Dev credentials
3. docker compose up (starts Redis + local Supabase via CLI)
4. uvicorn app.main:app --reload
5. Open http://localhost:8000/docs (Swagger UI)
```

### API Testing

**Swagger UI** (`/docs`): Available in development and staging environments for testing all endpoints. Disabled in production.

**Postman Collection**: A shared Postman workspace is maintained with:
- Environments: Local, Staging, Production (read-only in prod)
- Pre-request scripts: Automatically fetch and attach JWT token
- Test scripts: Verify response status, schema, and business logic

### Integration Testing (pytest)

| Test Suite | Coverage |
|------------|----------|
| `test_auth.py` | OTP flow, login, 2FA, token expiry, role extraction |
| `test_booking_engine.py` | All booking rules, advance days, person limits |
| `test_conflict_checker.py` | Kaapu/Kavasam, Chariot sessions, Thirukalyanam |
| `test_moolavar_abishegam.py` | Family limit, persons per family |
| `test_annadhanam.py` | Session capacity, duplicate prevention |
| `test_chariot.py` | Session exclusivity, all valid/invalid combinations |
| `test_ganapathy_homam.py` | Advance days, Chariot notice behavior |
| `test_calendar.py` | Blocked dates, partial dates, override rules |
| `test_e_undiyal.py` | Donation flow, receipt generation |
| `test_payment_webhooks.py` | Webhook signature verification, idempotency |
| `test_capacity.py` | Concurrent booking simulation (zero-overbooking) |
| `test_admin_rbac.py` | Role permission matrix for all admin endpoints |
| `test_audit_logs.py` | Verify audit log entries for all write operations |

### Concurrency / Zero-Overbooking Test

A dedicated load test simulates 50 concurrent booking requests for a slot with capacity = 5.

**Expected result:** Exactly 5 bookings are confirmed. All others receive a capacity-exceeded error. No overbooking occurs.

This test runs in the CI pipeline before every production deployment.

### Database Testing

- Tests run against a real Supabase Dev project (not a mock).
- Each test that writes data runs in a transaction that is rolled back at the end.
- Fixtures pre-populate services, slot_inventory, and test users.

### UAT Testing Plan

| Phase | Tester | Scope |
|-------|--------|-------|
| Phase 1: API Testing | Backend engineers | All endpoints via Swagger/Postman |
| Phase 2: Business Rule Testing | Temple admin representative | Booking rules, conflict rules, calendar |
| Phase 3: Payment Testing | Backend + payment team | Full payment flow with test credentials |
| Phase 4: Security Testing | Security engineer | Auth bypass, rate limits, webhook forgery |
| Phase 5: Load Testing | DevOps | 100 concurrent users, zero-overbooking verification |
| Phase 6: Admin UAT | Temple super admin | Full CMS walkthrough |

---

## 20. 3-Day Implementation Roadmap

### Pre-conditions

- Supabase Dev project created
- Railway account ready
- GitHub repository initialized
- Team access to payment gateway test account
- Environment variables documented and shared securely

---

### Day 1: Foundation, Database, Auth, and Core Services

**Objectives**
- Database schema fully deployed
- Authentication working end-to-end
- Service catalogue API live
- Basic booking engine skeleton in place

**Tasks**

| # | Task | Assignee | Duration |
|---|------|----------|----------|
| 1.1 | Initialize FastAPI project with all routers, directory structure | Backend Lead | 1 hour |
| 1.2 | Configure Pydantic settings, database connection, asyncpg | Backend | 1 hour |
| 1.3 | Deploy all database tables and indexes to Supabase Dev | DB Architect | 2 hours |
| 1.4 | Enable RLS on all tables; write and apply all RLS policies | DB Architect | 2 hours |
| 1.5 | Configure Supabase Auth: OTP, email/password, custom claims | Backend | 1.5 hours |
| 1.6 | Implement JWT verification dependency and role guards | Backend Lead | 1.5 hours |
| 1.7 | Implement admin 2FA (TOTP) middleware | Backend | 1 hour |
| 1.8 | Implement GET `/api/v1/services` with active service listing | Backend | 1 hour |
| 1.9 | Implement GET `/api/v1/availability` (calendar + capacity check) | Backend | 2 hours |
| 1.10 | Write Postman collection for auth and services endpoints | Backend | 1 hour |
| 1.11 | Deploy to Railway staging environment | DevOps | 1 hour |
| 1.12 | Run `test_auth.py` suite and verify all pass | Backend | 1 hour |

**Deliverables**
- All database tables live in Supabase Dev
- RLS policies applied and tested
- Auth API endpoints working
- Service and availability API live
- Postman collection for all Day 1 endpoints

**Risks**
- RLS policy complexity may require iteration
- Supabase Auth custom claims setup may need debugging

**Expected Outcome:** Team can authenticate as devotee and admin, fetch services, and check availability via Postman.

---

### Day 2: Booking Engine, Conflict Rules, E-Undiyal, and Payment Integration

**Objectives**
- Complete booking engine with all business rules
- All conflict checks implemented
- E-Undiyal donation flow working
- Payment gateway integrated (order creation + webhook)

**Tasks**

| # | Task | Assignee | Duration |
|---|------|----------|----------|
| 2.1 | Implement calendar service (date config, partial blocking) | Backend | 1.5 hours |
| 2.2 | Implement conflict checker service (Kaapu/Kavasam, Chariot, Thirukalyanam) | Backend Lead | 2 hours |
| 2.3 | Implement booking creation endpoint with all validation layers | Backend Lead | 2.5 hours |
| 2.4 | Implement slot inventory management with SELECT FOR UPDATE | Backend | 2 hours |
| 2.5 | Implement Moolavar Abishegam family/person validation | Backend | 1 hour |
| 2.6 | Implement Ganapathy Homam advance days + Chariot notice behavior | Backend | 1 hour |
| 2.7 | Implement Annadhanam session capacity + duplicate check | Backend | 1 hour |
| 2.8 | Implement E-Undiyal donation flow (create, webhook, receipt) | Backend | 1.5 hours |
| 2.9 | Implement payment order creation endpoint (Razorpay) | Backend | 1 hour |
| 2.10 | Implement payment webhook endpoint with HMAC verification | Backend Lead | 1.5 hours |
| 2.11 | Implement booking status promotion on payment success | Backend | 1 hour |
| 2.12 | Implement slot cleanup background job | Backend | 0.5 hours |
| 2.13 | Write `test_booking_engine.py`, `test_conflict_checker.py`, `test_annadhanam.py` | Backend | 1 hour |
| 2.14 | Run concurrency/zero-overbooking load test | DevOps | 0.5 hours |

**Deliverables**
- All booking business rules enforced on backend
- Conflict rules working for all documented scenarios
- E-Undiyal flow end-to-end
- Payment create-order and webhook working
- Test suites passing

**Risks**
- Concurrency test may reveal race conditions requiring transaction adjustments
- Payment gateway sandbox behavior may differ from production

**Expected Outcome:** Complete booking flow from authentication to payment confirmation is working end-to-end in staging.

---

### Day 3: CMS, Reporting, Notices, Security Hardening, and Production Readiness

**Objectives**
- Full CMS API live
- Reporting system core metrics working
- Notice management working
- Security controls verified
- Production deployment complete

**Tasks**

| # | Task | Assignee | Duration |
|---|------|----------|----------|
| 3.1 | Implement all admin booking management endpoints | Backend | 2 hours |
| 3.2 | Implement admin user management endpoints | Backend | 1 hour |
| 3.3 | Implement calendar management admin endpoints | Backend | 1 hour |
| 3.4 | Implement service management admin endpoints | Backend Lead | 1 hour |
| 3.5 | Implement slot inventory admin endpoints | Backend | 0.5 hours |
| 3.6 | Implement conflict rule management admin endpoints | Backend Lead | 0.5 hours |
| 3.7 | Implement notice management system + scheduler background job | Backend | 1.5 hours |
| 3.8 | Implement daily/weekly/monthly reporting endpoints + KPI dashboard | Backend | 2 hours |
| 3.9 | Implement audit log write on all sensitive operations | Backend | 1 hour |
| 3.10 | Implement rate limiting on all endpoints | DevOps | 1 hour |
| 3.11 | Security review: verify RLS, verify CORS, verify webhook signatures | Security | 1 hour |
| 3.12 | Run full `test_admin_rbac.py` suite | Backend | 0.5 hours |
| 3.13 | Configure CI/CD pipeline (GitHub Actions) | DevOps | 1 hour |
| 3.14 | Configure production environment variables in Railway | DevOps | 0.5 hours |
| 3.15 | Deploy to production; run health checks | DevOps | 0.5 hours |
| 3.16 | Production readiness checklist review | Backend Lead | 0.5 hours |

**Deliverables**
- All CMS endpoints live and tested
- Reporting system returning correct data
- Notice management working
- Rate limiting active
- Security controls verified
- Production environment live with health check passing
- CI/CD pipeline active

**Risks**
- Reporting queries may need optimization for large datasets
- Production Supabase connectivity may require firewall configuration

**Expected Outcome:** Fully functional backend API ready for frontend integration. Admin can manage all aspects of the temple platform via CMS API.

---

## 21. Production Readiness Checklist

### Database

- [ ] All tables created with correct columns, types, and constraints
- [ ] All indexes created for foreign keys and frequently-queried columns
- [ ] RLS enabled on all tables
- [ ] RLS policies verified for each role
- [ ] Audit log table is append-only (GRANT verified)
- [ ] Database backups enabled (Supabase Pro)
- [ ] Migration scripts committed and versioned
- [ ] Rollback scripts written for each migration

### Security

- [ ] No secrets committed to version control
- [ ] All environment variables set in production
- [ ] JWT verification tested with expired and invalid tokens
- [ ] Admin 2FA mandatory and tested
- [ ] Rate limiting active and tested
- [ ] CORS allowlist contains only production domains
- [ ] HTTPS enforced
- [ ] Webhook HMAC verification tested
- [ ] Duplicate booking prevention tested with concurrent requests
- [ ] Zero-overbooking load test passed

### Business Rules

- [ ] Advance booking days enforced for all services
- [ ] Max 5 persons per booking enforced
- [ ] Moolavar Abishegam: 10 families × 3 persons enforced
- [ ] Kaapu/Kavasam mutual exclusivity enforced
- [ ] Chariot session exclusivity enforced (one per session)
- [ ] Thirukalyanam blocks morning chariot enforced
- [ ] Ganapathy Homam 5-day advance enforced
- [ ] Ganapathy Homam + Chariot notice behavior verified
- [ ] Annadhanam session capacity enforced
- [ ] Annadhanam duplicate booking prevention verified
- [ ] Annadhanam Meals 1-person limit enforced
- [ ] E-Undiyal completely separate from bookings (verified in routing)
- [ ] Post-booking Kaapu info (11:00 AM / 5:45 PM) stored and retrievable

### Operations

- [ ] Health check endpoint (`GET /api/v1/health`) returning 200
- [ ] All background jobs running (slot cleanup, notice scheduler)
- [ ] CI/CD pipeline active and tested with a sample deployment
- [ ] Monitoring and alerting configured (uptime, error rate, latency)
- [ ] Log aggregation configured (Railway logs or external log service)
- [ ] On-call runbook documented for common incidents
- [ ] Rollback procedure documented and tested

### Payments

- [ ] Payment gateway test mode verified end-to-end
- [ ] Payment gateway production keys configured
- [ ] Webhook URL registered in payment gateway dashboard
- [ ] Refund flow tested
- [ ] Payment receipt PDF generation verified
- [ ] E-Undiyal donation receipt generation verified

### Documentation

- [ ] Postman collection covers all endpoints
- [ ] Swagger UI accurate and complete
- [ ] API versioning applied (`/api/v1/`)
- [ ] Environment setup README up-to-date
- [ ] Deployment runbook documented

---

*Document prepared for Sri Manakula Vinayagar Devasthanam engineering team.*  
*This document covers backend architecture only. Frontend implementation is a separate project and scope.*  
*All business rules in this document supersede any prior verbal or informal specifications.*

---

## 22. 80G Income Tax Exemption — Post-Payment Flow

### 22.1 Overview

Every successful E-Undiyal (donation) payment must immediately communicate to the donor that their contribution qualifies for an **Income Tax deduction under Section 80G of the Income Tax Act, 1961**. The certificate delivery method depends on whether the donor is physically present in Pondicherry, located elsewhere in India, or residing abroad.

This flow is **fully managed by the backend**. The frontend only renders what the API returns.

---

### 22.2 Immediate Post-Payment Response

**Trigger:** `payment.captured` webhook received and verified for an E-Undiyal transaction.

As part of the `complete_donation()` service call, the API response and all notifications must include the following **80G notice**:

```
"This donation qualifies for an Income Tax deduction under Section 80G
 of the Income Tax Act, 1961. Sri Manakula Vinayagar Devasthanam is a
 registered charitable institution. Your 80G tax exemption certificate
 will be issued against this donation.

 Reference Number: SMV-EU-YYYY-NNNN
 Amount: ₹{amount}
 Date: {date}"
```

**Frontend display requirement (backend instruction):**

The `complete_donation` API response must include:

```json
{
  "transaction_id": "<uuid>",
  "transaction_reference": "SMV-EU-2026-0042",
  "status": "success",
  "amount_paise": 500000,
  "amount_display": "₹5,000",
  "tax_certificate": {
    "eligible": true,
    "section": "80G — Income Tax Act, 1961",
    "institution_name": "Sri Manakula Vinayagar Devasthanam",
    "registration_number": "<80G registration number>",
    "message": "This donation qualifies for Income Tax exemption under Section 80G. Your certificate will be issued and delivered based on your location preference.",
    "next_step": "Please confirm your certificate delivery preference."
  },
  "certificate_status": "pending_details"
}
```

**SMS sent to donor immediately:**

```
Sri Manakula Vinayagar Devasthanam — Thank you for your generous donation of
₹{amount} (Ref: SMV-EU-2026-0042).

Your donation qualifies for Income Tax exemption under Section 80G of the
Income Tax Act, 1961.

To receive your 80G certificate, please visit: {certificate_preference_link}
```

**Email sent to donor (if email provided):**

Subject: `80G Tax Exemption Certificate — Donation Receipt [SMV-EU-2026-0042]`

Body includes:
- Donation amount and date
- 80G registration number of the temple
- Clear statement: *"This donation is eligible for deduction under Section 80G of the Income Tax Act, 1961"*
- Link to submit delivery preference
- Temple's address and contact for queries

---

### 22.3 Certificate Delivery — Location-Based Routing

After payment confirmation, the donor is prompted to select their location type. The backend routes the certificate delivery accordingly.

**API endpoint:** `POST /api/v1/e-undiyal/{transaction_id}/certificate-preference`

**Request body:**
```json
{
  "donor_location_type": "local" | "domestic" | "international",
  "donor_address": {
    "full_name": "string",
    "door_no": "string",
    "street": "string",
    "city": "string",
    "state": "string",
    "pincode": "string",
    "country": "string",
    "phone": "string",
    "pan_number": "string (optional but encouraged for 80G)"
  }
}
```

---

#### Case 1 — Donor is in Pondicherry (Local)

**`donor_location_type: "local"`**

**Backend action:**
- Set `delivery_mode = "in_person"`
- Set `certificate_status = "processing"`
- No address required

**Response message to donor:**

```
Your 80G tax exemption certificate is being prepared.

Please visit the temple office with:
  • Your original payment receipt (or this SMS/email as proof)
  • A valid government-issued photo ID (Aadhaar / PAN / Passport)

Temple Office: Sri Manakula Vinayagar Devasthanam, Puducherry — 605 001
Office Hours: Monday to Saturday, 9:00 AM to 5:00 PM

Your certificate number: SMV-80G-2026-NNNN will be ready within 3 working days.
Please call +91-XXXXXXXXXX before visiting to confirm availability.
```

**SMS:**
```
Your 80G certificate (SMV-80G-2026-NNNN) will be ready for in-person collection
at the temple office. Office hrs: 9AM–5PM, Mon–Sat. Bring photo ID.
Queries: +91-XXXXXXXXXX
```

---

#### Case 2 — Donor is in India but outside Pondicherry (Domestic)

**`donor_location_type: "domestic"`**

**Backend validation:**
- `donor_address` is **mandatory**
- `pincode` must be exactly 6 digits
- `pan_number` format validated: `[A-Z]{5}[0-9]{4}[A-Z]{1}` (PAN is strongly recommended for 80G claim; backend should warn if not provided but not block)
- `state` must be a valid Indian state name

**Backend action:**
- Set `delivery_mode = "courier"`
- Store full address in `donor_address` JSONB column
- Set `certificate_status = "processing"`

**Response message to donor:**

```
Your 80G tax exemption certificate will be dispatched to the following address
via registered courier:

  {full_name}
  {door_no}, {street}
  {city} — {pincode}
  {state}, India

Expected delivery: 7 to 10 working days from date of dispatch.

You will receive a courier tracking number via SMS and email once dispatched.
Certificate number: SMV-80G-2026-NNNN

Note: Please ensure someone is available to receive the courier at the above
address. The certificate is a legal document — do not share it unnecessarily.
```

**SMS:**
```
Your 80G certificate will be dispatched to {city} — {pincode} via courier
within 7–10 working days. Tracking ID will be sent once dispatched.
Ref: SMV-EU-2026-0042
```

---

#### Case 3 — Donor is Outside India (International / NRI)

**`donor_location_type: "international"`**

**Backend validation:**
- `donor_address` is **mandatory**
- `country` must not be "India"
- `phone` should be in E.164 international format
- PAN number is optional (NRIs may not have Indian PAN)

**Backend action:**
- Set `delivery_mode = "courier"`
- Store full international address in `donor_address` JSONB column
- Set `certificate_status = "processing"`

**Response message to donor:**

```
Your 80G tax exemption certificate will be dispatched to your international
address via registered international courier:

  {full_name}
  {door_no}, {street}, {city}
  {country}

Expected delivery: 10 to 21 working days from date of dispatch.
(Delivery time varies by country and customs processing.)

A courier tracking number will be sent to your registered phone and email
once dispatched.

Certificate number: SMV-80G-2026-NNNN

For international donors: This certificate is issued under Section 80G of the
Indian Income Tax Act, 1961. For tax benefit eligibility in your country of
residence, please consult a local tax advisor.
```

**SMS:**
```
Your 80G certificate will be dispatched to {country} via international courier.
Delivery: 10–21 working days. Tracking will be shared via SMS & email.
Ref: SMV-EU-2026-0042
```

---

### 22.4 Certificate Delivery Status Lifecycle

```
Donation Payment Confirmed
          │
          ▼
  certificate_status = "pending_details"
  (Donor prompted to submit delivery preference)
          │
          ▼ (Donor submits preference)
  certificate_status = "processing"
  (Admin team prepares the certificate)
          │
          ▼ (Admin issues certificate via CMS)
  certificate_status = "ready"
  (PDF generated, stored in Supabase Storage)
  (Donor notified with download link + dispatch ETA)
          │
     ┌────┴────────────────────────────────────┐
     │                                         │
     ▼ (in_person)                             ▼ (courier)
  Donor collects at temple               certificate_status = "dispatched"
  Admin marks: "collected"               (Tracking ID sent to donor)
  certificate_status = "delivered"              │
                                               ▼
                                    certificate_status = "delivered"
                                    (After courier confirmation)
```

### 22.5 Admin Certificate Management

The CMS provides the admin panel to manage the certificate queue:

| Admin Action | CMS Route | Who Can Do It |
|-------------|-----------|---------------|
| View all pending certificates | `GET /admin/certificates?status=processing` | admin, super_admin |
| Issue certificate (generate PDF) | `POST /admin/certificates/{id}/issue` | admin, super_admin |
| Mark dispatched (add tracking) | `POST /admin/certificates/{id}/dispatch` | admin, super_admin |
| Mark collected (in-person) | `POST /admin/certificates/{id}/collected` | admin, super_admin |
| Download certificate PDF | `GET /admin/certificates/{id}/download` | admin, super_admin |

**Certificate PDF content (generated by backend):**

```
Sri Manakula Vinayagar Devasthanam
[Temple Logo]
Puducherry — 605 001

80G TAX EXEMPTION CERTIFICATE

Certificate Number: SMV-80G-2026-NNNN
Date of Issue: DD/MM/YYYY

This is to certify that:

Donor Name:     {full_name}
PAN Number:     {pan_number or "Not Provided"}
Phone:          {phone}
Email:          {email or "Not Provided"}

has made a charitable donation of ₹{amount} (Rupees {amount_in_words} only)
on {donation_date} via reference number {transaction_reference}.

This donation is eligible for deduction under Section 80G of the
Income Tax Act, 1961.

80G Registration Number: {temple_80g_registration_number}
Validity: Financial Year YYYY–YYYY

Authorised Signatory
Executive Officer
Sri Manakula Vinayagar Devasthanam
```

---

## 23. Total Infrastructure Cost — Production Architecture

### 23.1 What Needs to Be Purchased

The following table lists every service required for the production backend to operate. All prices are as of June 2026.

---

### 23.2 One-Time Setup Costs

| Item | Purpose | Estimated Cost | Remarks |
|------|---------|---------------|---------|
| **DLT Registration (MSG91/Airtel)** | Mandatory for sending bulk SMS in India (TRAI regulation) | ₹5,000 – ₹8,000 | One-time. Required before any SMS can be sent to devotees. Apply at https://www.trai.gov.in |
| **SMS Template Approval (DLT)** | Each SMS template must be individually approved | ₹0 – ₹500 | Usually free; small fee on some operators. Estimate 10 templates |
| **Domain Name** (`smvd.in` or similar) | Production API domain | ₹800 – ₹1,500/year | If not already owned. Renewal annually |
| **Razorpay KYC / Live Account** | Activate live payment mode | ₹0 | Free to activate. Requires temple GST, PAN, bank details. Submit at razorpay.com |
| **SSL Certificate** | HTTPS for API | ₹0 | Auto-managed by Cloudflare (free) |

**One-Time Total: ₹6,000 – ₹10,000**

---

### 23.3 Monthly Recurring Costs

#### Tier 1 — Core Infrastructure (Mandatory)

| Service | Plan | Monthly Cost (USD) | Monthly Cost (INR ~₹83/USD) | What You Get |
|---------|------|-------------------|-----------------------------|-------------|
| **Railway.app** (Backend hosting) | Hobby → Pro | $5 – $20 | ₹415 – ₹1,660 | FastAPI backend hosting. Hobby plan sufficient for low-medium traffic. Upgrade to Pro ($20) if concurrent users exceed 50 |
| **Supabase** (Database + Auth + Storage) | **Pro** | $25 | ₹2,075 | PostgreSQL + Auth + Storage + **daily backups** + 100K MAU. **Pro is mandatory** — Free plan has no backups and limited connections |
| **Razorpay** (Payment gateway) | Transaction-based | 2% per transaction | Varies | No monthly fee. 2% of each booking/donation amount. International cards: 3% |
| **Cloudflare** (CDN + DDoS + WAF) | Free | $0 | ₹0 | DDoS protection, CDN, SSL. Free tier sufficient for this project |

**Core Monthly Total: $30 – $45 (₹2,490 – ₹3,735)**

---

#### Tier 2 — Communication Services

| Service | Plan | Monthly Cost | What You Get |
|---------|------|-------------|-------------|
| **MSG91** (SMS — OTP + Notifications) | Pay-as-you-go | ₹0.20 – ₹0.45 per SMS | Transactional SMS for OTP, booking confirmation, certificate dispatch. Estimate 500 SMS/month = ₹100 – ₹225/month |
| **Resend** (Email — receipts + 80G certs) | Free → Pro | $0 – $20 | Free: 3,000 emails/month. Pro ($20/month): 50,000 emails. Start with Free; upgrade when volume exceeds 3,000/month |

**Communication Monthly Total: ₹100 – ₹1,800 (depending on volume)**

---

#### Tier 3 — Monitoring and Operations

| Service | Plan | Monthly Cost | What You Get |
|---------|------|-------------|-------------|
| **Sentry** (Error tracking) | Free → Team | $0 – $26 | Free: 5,000 errors/month (sufficient for initial launch). Team ($26/month) if error volume exceeds limit |
| **UptimeRobot** (Uptime monitoring) | Free | $0 | 50 monitors, 5-minute checks, email alerts. Free tier is sufficient |
| **GitHub** (Source control + CI/CD) | Free | $0 | Unlimited public + private repos. 2,000 CI/CD minutes/month (free). Sufficient for this team size |

**Monitoring Monthly Total: $0 (free tier sufficient at launch)**

---

### 23.4 Monthly Cost Summary

| Category | Low Estimate (INR) | High Estimate (INR) | Notes |
|----------|-------------------|---------------------|-------|
| Core Infrastructure | ₹2,490 | ₹3,735 | Railway + Supabase + Razorpay fixed costs |
| Razorpay Fees (variable) | ₹1,000 | ₹10,000+ | Depends on booking and donation volume |
| SMS (MSG91) | ₹100 | ₹500 | Depends on transaction volume |
| Email (Resend) | ₹0 | ₹1,660 | Free up to 3,000/month |
| Monitoring (Sentry + UptimeRobot) | ₹0 | ₹2,158 | Free tier covers launch period |
| Domain renewal | ₹67 | ₹125 | ₹800–1,500 amortised monthly |
| **TOTAL MONTHLY (Fixed)** | **~₹2,700** | **~₹8,200** | Excluding variable Razorpay fees |
| **TOTAL MONTHLY (with Razorpay est.)** | **~₹3,700** | **~₹18,200** | Depends on revenue volume |

---

### 23.5 Annual Cost Estimate

| Period | Low Estimate (INR) | High Estimate (INR) |
|--------|-------------------|---------------------|
| One-time setup | ₹6,000 | ₹10,000 |
| Monthly × 12 (fixed only) | ₹32,400 | ₹98,400 |
| **Year 1 Total** | **~₹38,400** | **~₹1,08,400** |

> Razorpay fees are excluded from annual totals as they are a percentage of revenue — not a fixed cost. At 2% per transaction, every ₹1,00,000 collected generates ₹2,000 in gateway fees.

---

### 23.6 Recommended Starting Configuration (Day 14 — Go-Live)

Start with this configuration. Scale up only when usage demands it.

| Service | Plan | Monthly Cost (INR) |
|---------|------|-------------------|
| Railway | Hobby ($5) | ₹415 |
| Supabase | **Pro ($25)** — non-negotiable for backups | ₹2,075 |
| Cloudflare | Free | ₹0 |
| MSG91 | Pay-as-you-go | ₹100 – ₹300 |
| Resend | Free (3K emails/month) | ₹0 |
| Sentry | Free (5K errors/month) | ₹0 |
| UptimeRobot | Free | ₹0 |
| GitHub | Free | ₹0 |
| **Starting Monthly Total** | | **~₹2,590 – ₹2,790** |

---

### 23.7 When to Scale Up (Triggers)

| Metric | Current Plan Limit | Upgrade To | Cost Impact |
|--------|-------------------|-----------|-------------|
| Railway CPU > 80% consistently | Hobby (0.5 vCPU) | Pro ($20/month) | +₹1,245/month |
| Supabase DB connections > 60 | Pro (60 connections) | Add connection pooling or Team plan | +₹0 (PgBouncer already included) |
| SMS volume > 2,000/month | Pay-as-you-go | Negotiate bulk rate with MSG91 | ₹0.15/SMS at bulk |
| Email > 3,000/month | Resend Free | Resend Pro ($20/month) | +₹1,660/month |
| Errors > 5,000/month | Sentry Free | Sentry Team ($26/month) | +₹2,158/month |

---

### 23.8 Razorpay Fee Impact by Revenue

| Monthly Revenue (INR) | Razorpay Fee (2%) | Net Revenue |
|----------------------|-------------------|-------------|
| ₹50,000 | ₹1,000 | ₹49,000 |
| ₹1,00,000 | ₹2,000 | ₹98,000 |
| ₹5,00,000 | ₹10,000 | ₹4,90,000 |
| ₹10,00,000 | ₹20,000 | ₹9,80,000 |

> Note: Razorpay offers negotiated rates below 2% for high-volume merchants. Once monthly GMV (Gross Merchandise Value) exceeds ₹5,00,000, contact Razorpay for a custom pricing discussion.

---

### 23.9 Total Budget Summary (Year 1)

```
One-Time Setup Costs:
  DLT Registration (SMS)         ₹5,000 – ₹8,000
  Domain Registration (1 year)   ₹800 – ₹1,500
  ─────────────────────────────────────────────
  One-Time Total                 ₹5,800 – ₹9,500

Monthly Fixed Costs (×12):
  Railway Hobby                  ₹415/month × 12 = ₹4,980
  Supabase Pro                   ₹2,075/month × 12 = ₹24,900
  Communication (SMS + Email)    ₹300/month × 12 = ₹3,600
  ─────────────────────────────────────────────
  Annual Fixed Total             ₹33,480

Variable Costs (payment gateway):
  Razorpay 2% of revenue         Depends on bookings/donations

─────────────────────────────────────────────────────────
YEAR 1 TOTAL (excluding Razorpay variable fees):
  Minimum: ₹5,800 + ₹33,480 = ₹39,280
  Maximum: ₹9,500 + ₹50,000 = ₹59,500 (with upgrades)
─────────────────────────────────────────────────────────
```

> **In simple terms:** Running this backend in production costs approximately **₹3,000 – ₹5,000 per month** in fixed infrastructure. Razorpay fees are an additional percentage of every transaction collected through the platform.

---

*Sections 22 and 23 added: June 2026*  
*Section 22 covers the 80G Income Tax Exemption certificate delivery flow.*  
*Section 23 covers the complete infrastructure cost breakdown for production deployment.*
