# Sri Manakula Vinayagar Devasthanam
## Backend — Technology Stack Declaration
**Prepared for:** National Informatics Centre (NIC) — Server Compatibility Review  
**Document Type:** Backend Technology Stack Brief  
**Date:** July 2026  
**Scope:** Backend API Server (`smvd-backend`)

---

## 1. Application Overview

The SMVD backend is a **REST API server** built with FastAPI (Python). It serves as the authoritative business logic layer for the temple's Online Services Portal — handling bookings, payments, authentication, calendar management, and administrative operations. It communicates with a managed PostgreSQL database (Supabase) and external gateways (Razorpay). The frontend (a separate Next.js application) calls this API over HTTPS.

---

## 2. Core Runtime

| Item | Value |
|------|-------|
| **Language** | Python `3.11` |
| **Framework** | FastAPI `0.111.0` |
| **ASGI Server** | Uvicorn `0.29.0` (with `uvicorn[standard]` — includes `uvloop` and `httptools`) |
| **Process Manager** | Systemd / Docker (see Section 7) |
| **Port** | `8000` (configurable) |

> **Key point for NIC:** The server requires **Python 3.11** installed on the host. It is started with `uvicorn app.main:app --host 0.0.0.0 --port 8000`. A reverse proxy (Nginx) must sit in front for HTTPS termination.

---

## 3. Full Dependency List (Production)

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | `0.111.0` | Core web framework — routing, validation, dependency injection |
| `uvicorn[standard]` | `0.29.0` | ASGI production server |
| `asyncpg` | `0.29.0` | Async PostgreSQL driver (direct Supabase DB connection) |
| `pydantic` | `2.7.0` | Request/response validation and serialisation |
| `pydantic-settings` | `2.2.1` | Environment variable configuration |
| `python-jose[cryptography]` | `3.3.0` | JWT decoding and signature verification |
| `httpx` | `0.27.0` | Async HTTP client (Supabase Auth API, MSG91, Resend) |
| `slowapi` | `0.1.9` | Rate limiting middleware |
| `APScheduler` | `3.10.4` | Scheduled background jobs (cleanup, reminders) |
| `WeasyPrint` | `62.3` | HTML-to-PDF for booking receipts and donation certificates |
| `razorpay` | `1.4.1` | Razorpay payment gateway SDK |
| `python-multipart` | `0.0.9` | File upload support |
| `sentry-sdk[fastapi]` | `1.45.0` | Error monitoring and alerting |
| `alembic` | `1.13.1` | Database migration management |

---

## 4. Database

| Item | Value |
|------|-------|
| **Database Engine** | PostgreSQL 15 (managed via Supabase) |
| **Connection Method** | `asyncpg` connection pool — connects via PgBouncer (port `6543`) |
| **Connection Pool** | min=5, max=20, command_timeout=60s |
| **ORM** | None — raw SQL via `asyncpg` for maximum performance and control |
| **Migrations** | Alembic (12 migration files, schema versioned) |
| **Row-Level Security** | Enabled on all tables via Supabase RLS policies |
| **Transactions** | `asyncpg` native transactions with `SELECT FOR UPDATE` row locking for zero-overbooking guarantee |

> **NIC Note:** The backend does not need PostgreSQL installed on the NIC server. It connects to an **external managed Supabase PostgreSQL** instance over the network. NIC's server only needs outbound TCP access to the Supabase host on port `6543`.

---

## 5. Authentication

| Method | Technology |
|--------|------------|
| **Devotee Login** | Phone OTP via MSG91 (custom flow) |
| **Admin Login** | Email + Password + TOTP 2FA (Google Authenticator) |
| **Token Format** | JWT (RS256) — issued by Supabase Auth |
| **JWT Verification** | `python-jose` verifying against Supabase JWKS endpoint |
| **Role Enforcement** | FastAPI dependency injection — `devotee → staff → admin → super_admin` |

---

## 6. External Services Called by the Backend

The backend server makes outbound HTTPS calls to the following external services at runtime:

| Service | Purpose | Protocol |
|---------|---------|---------|
| Supabase PostgreSQL | Database (read/write) | TCP 6543 |
| Supabase Auth API | JWT key retrieval (JWKS, cached 1hr) | HTTPS |
| Supabase Storage | Receipt/certificate PDF upload | HTTPS |
| Razorpay API | Create payment orders, initiate refunds | HTTPS |
| MSG91 | Send OTP SMS to devotees | HTTPS |
| Resend / SMTP | Admin email notifications | HTTPS |
| Sentry | Error telemetry | HTTPS |

> **NIC Action Required:** Ensure outbound HTTPS (port 443) and TCP port 6543 are not firewalled on the server hosting the backend.

---

## 7. Startup & Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Recommended architecture on NIC server:**

```
Internet
    |
    v
[ NIC Nginx — HTTPS on port 443 ]
  - SSL termination
  - proxy_pass to http://localhost:8000
    |
    v
[ Uvicorn — FastAPI app on port 8000 ]
  - 4 worker processes
  - Python 3.11
    |
    v
[ Supabase Cloud — PostgreSQL 15 ] (external, managed)
```

---

## 8. Operating System & Server Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Ubuntu 20.04 LTS / RHEL 8 | Ubuntu 22.04 LTS |
| **Python** | 3.11 | 3.11.x latest patch |
| **RAM** | 1 GB | 2–4 GB |
| **CPU** | 1 vCPU | 2 vCPU |
| **Disk** | 5 GB | 20 GB (for logs, PDFs) |
| **Outbound HTTPS** | Required | — |
| **Nginx** | Recommended | Required for HTTPS |

### OS Compatibility

| OS | Compatible? |
|----|-------------|
| Ubuntu 20.04 LTS | Yes |
| Ubuntu 22.04 LTS | Yes — Recommended |
| RHEL / CentOS 8, 9 | Yes |
| Debian 11 / 12 | Yes |
| Windows Server | Not recommended |

---

## 9. Environment Variables Required

```env
DATABASE_URL=postgresql+asyncpg://...        # Supabase PgBouncer URL
SUPABASE_URL=https://xxx.supabase.co         # Supabase project URL
SUPABASE_SERVICE_ROLE_KEY=...               # Backend-only admin key
SUPABASE_JWT_SECRET=...                     # For JWT verification
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
MSG91_API_KEY=...
RESEND_API_KEY=...
ENVIRONMENT=production
ALLOWED_ORIGINS=https://smvd.nic.in
SENTRY_DSN=...
```

> All secrets are loaded from a `.env` file on the server. This file is **never committed to version control**.

---

## 10. Summary for NIC Review

| Question | Answer |
|----------|--------|
| What runtime is required? | **Python 3.11** |
| How is it started? | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| What port does it listen on? | **8000** (proxied from 443 via Nginx) |
| Does it need a database on NIC server? | **No** — connects to external Supabase PostgreSQL |
| Does it need Redis / queue broker? | No |
| Does it need Node.js? | **No** |
| What outbound ports are needed? | 443 (HTTPS to Supabase, Razorpay, MSG91) and 6543 (Supabase DB) |
| Is a reverse proxy needed? | **Yes — Nginx required** for HTTPS termination |
| RAM required | 1 GB minimum, 2 GB recommended |
| Disk required | 5 GB minimum |

---

*Document prepared by: SMVD Backend Development Team*  
*For technical queries, contact the project lead prior to NIC deployment.*
