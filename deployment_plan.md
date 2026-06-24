# Sri Manakula Vinayagar Devasthanam — Deployment Plan

**Project:** Temple Booking Platform Backend  
**Owner:** Abhinav (DevOps Lead)  
**Hosting:** Railway.app + Supabase + Cloudflare  

---

## Table of Contents

1. [Local Development Setup](#1-local-development-setup)
2. [Staging Setup](#2-staging-setup)
3. [Production Setup](#3-production-setup)
4. [Deployment Pipeline (CI/CD)](#4-deployment-pipeline-cicd)
5. [Monitoring and Logging](#5-monitoring-and-logging)
6. [Rollback Procedures](#6-rollback-procedures)
7. [Backup Strategy](#7-backup-strategy)
8. [Production Checklist](#8-production-checklist)

---

## 1. Local Development Setup

### 1.1 Prerequisites

Install on your machine:
- Python 3.11+ (`python3 --version`)
- Git (`git --version`)
- `pip` and `venv`
- curl or Postman (for API testing)
- Supabase CLI (optional, for local DB inspection)

```bash
# Verify Python version
python3 --version    # Must be 3.11 or higher

# Install Supabase CLI (optional)
brew install supabase/tap/supabase
```

### 1.2 Clone and Set Up

```bash
# Clone repository
git clone https://github.com/your-org/smvd-backend.git
cd smvd-backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate.bat    # Windows

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your values
nano .env   # or open in your editor
```

Minimum required values for local development:

```env
# Supabase (get from Abhinav — shared Supabase Dev project)
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Razorpay (use TEST MODE keys)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_test_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Notifications (can be test/dummy values for local)
MSG91_API_KEY=your_msg91_key
RESEND_API_KEY=re_xxxxxxxxxxxx

# App settings
ENVIRONMENT=local
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
SENTRY_DSN=    # Leave empty for local
```

### 1.4 Database Setup (Local)

```bash
# Activate venv if not already active
source venv/bin/activate

# Apply all migrations to Supabase Dev DB
alembic upgrade head

# Verify in Supabase dashboard:
# 1. Open https://app.supabase.com
# 2. Select the Dev project
# 3. Go to Table Editor
# 4. Verify all 11 tables exist
# 5. Go to SQL Editor → run: SELECT * FROM services;
# 6. Should see 10 service rows (from seed migration)
```

### 1.5 Run the Development Server

```bash
# Make sure venv is active
source venv/bin/activate

# Run with hot reload (auto-restarts on code changes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345] using statreload
# INFO:     Started server process [12346]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

### 1.6 Verify Local Setup

```bash
# Health check
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok","environment":"local","db":"connected","version":"1.0.0"}

# Services list
curl http://localhost:8000/api/v1/services
# Expected: JSON array with 10 services

# Open Swagger docs
open http://localhost:8000/docs
# Interactive API documentation — use for manual testing
```

### 1.7 Running Tests Locally

```bash
# Unit tests only (fast — run before every PR)
pytest tests/unit/ -v

# All tests (slower — run before staging merge)
pytest tests/ -v

# With coverage
pytest tests/unit/ --cov=app --cov-report=term-missing

# Specific test
pytest tests/unit/test_booking_engine.py::test_create_booking_success -v
```

### 1.8 Common Local Issues and Fixes

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Connection refused` to DB | Check `DATABASE_URL` in `.env` |
| `JWT signature verification failed` | Check `SUPABASE_JWT_SECRET` value |
| Port 8000 already in use | `lsof -ti:8000 \| xargs kill -9` then restart |
| Alembic migration error | Check DB connection + migration file syntax |
| `asyncpg.create_pool failed` | Verify PgBouncer port (6543) not direct port (5432) |

---

## 2. Staging Setup

### 2.1 Supabase Staging Project

Create a **separate Supabase project** for staging (not the same as dev):
1. Go to https://app.supabase.com → New Project
2. Name: `smvd-staging`
3. Region: Southeast Asia (Singapore) — same as production
4. Note: URL, anon key, service_role key, JWT secret

Apply migrations to staging:
```bash
# Set DATABASE_URL to staging database
export DATABASE_URL=postgresql://postgres.[staging-ref]:...@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

alembic upgrade head

# Seed staging data (same as production seed)
# Migration 011 handles this automatically
```

### 2.2 Railway Staging Service

1. Go to https://railway.app → New Project
2. Name: `smvd-backend-staging`
3. Add a Service → GitHub Repository → `smvd-backend`
4. Set deployment branch: `staging`
5. Add all environment variables (from staging `.env` values)

**Railway Environment Variables for Staging:**
```
SUPABASE_URL=<staging project URL>
SUPABASE_SERVICE_ROLE_KEY=<staging service role key>
SUPABASE_ANON_KEY=<staging anon key>
SUPABASE_JWT_SECRET=<staging JWT secret>
DATABASE_URL=<staging PgBouncer URL with port 6543>
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
RAZORPAY_KEY_SECRET=<test secret>
RAZORPAY_WEBHOOK_SECRET=<test webhook secret>
MSG91_API_KEY=<key>
RESEND_API_KEY=<key>
ENVIRONMENT=staging
ALLOWED_ORIGINS=https://staging.smvd.in,http://localhost:3000
SENTRY_DSN=<staging Sentry DSN>
PORT=8000
```

### 2.3 Custom Domain for Staging

1. In Railway → Settings → Networking → Custom Domain
2. Add: `staging-api.smvd.in`
3. In Cloudflare (or your DNS) → Add CNAME: `staging-api` → Railway URL
4. Enable SSL: auto-managed by Railway

### 2.4 Staging Health Check

After first deployment:
```bash
curl https://staging-api.smvd.in/api/v1/health
# Expected: {"status":"ok","environment":"staging","db":"connected"}

curl https://staging-api.smvd.in/api/v1/services
# Expected: 10 services

curl https://staging-api.smvd.in/api/v1/notices
# Expected: [] (empty, no notices yet)
```

### 2.5 Razorpay Staging Webhook

In Razorpay Test Dashboard:
1. Settings → Webhooks → Add Webhook
2. URL: `https://staging-api.smvd.in/api/v1/webhooks/payment/razorpay`
3. Events: `payment.captured`, `payment.failed`
4. Secret: copy the `RAZORPAY_WEBHOOK_SECRET` value
5. Test the webhook with Razorpay's test button

---

## 3. Production Setup

### 3.1 Supabase Production Project

Create a **Supabase Pro project** for production:
1. Go to https://app.supabase.com → New Project
2. Name: `smvd-production`
3. Plan: **Pro** (required for daily backups and higher limits)
4. Region: Southeast Asia (Singapore) — lowest latency for India
5. Note all credentials securely (Bitwarden or equivalent)

Apply migrations:
```bash
export DATABASE_URL=postgresql://postgres.[prod-ref]:...@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
alembic upgrade head
```

Verify `audit_logs` INSERT-only grant:
```sql
-- In Supabase SQL Editor for production project:
REVOKE UPDATE, DELETE ON audit_logs FROM service_role;
REVOKE TRUNCATE ON audit_logs FROM service_role;

-- Test it works:
SELECT * FROM audit_logs LIMIT 1;  -- Should work (SELECT allowed)
DELETE FROM audit_logs WHERE FALSE; -- Should fail (DELETE denied)
```

### 3.2 Railway Production Service

1. Railway → New Project → `smvd-backend-production`
2. Add Service → GitHub Repository → `smvd-backend`
3. Set deployment branch: `main`
4. Configure scaling: Start with 1 instance, 1GB RAM, 1 vCPU

**Production Environment Variables:**
```
SUPABASE_URL=<production URL>
SUPABASE_SERVICE_ROLE_KEY=<production service role key>
SUPABASE_ANON_KEY=<production anon key>
SUPABASE_JWT_SECRET=<production JWT secret>
DATABASE_URL=<production PgBouncer URL>
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxx   # LIVE keys for production
RAZORPAY_KEY_SECRET=<live secret>
RAZORPAY_WEBHOOK_SECRET=<live webhook secret>
MSG91_API_KEY=<production key>
RESEND_API_KEY=<production key>
ENVIRONMENT=production
ALLOWED_ORIGINS=https://smvd.in,https://www.smvd.in
SENTRY_DSN=<production Sentry DSN>
PORT=8000
```

### 3.3 Custom Domain for Production

1. Railway → Settings → Networking → Custom Domain
2. Add: `api.smvd.in`
3. In Cloudflare:
   - Add CNAME: `api` → Railway production URL
   - Enable Cloudflare proxy (orange cloud)
   - SSL/TLS mode: Full (strict)
   - Enable Cloudflare WAF (Web Application Firewall)

### 3.4 Razorpay Production Webhook

In Razorpay Live Dashboard:
1. Settings → Webhooks → Add Webhook
2. URL: `https://api.smvd.in/api/v1/webhooks/payment/razorpay`
3. Events: `payment.captured`, `payment.failed`, `refund.created`
4. Secret: production `RAZORPAY_WEBHOOK_SECRET`

> **IMPORTANT:** Ensure Razorpay KYC is complete and live keys are approved before Day 14.

### 3.5 Dockerfile

```dockerfile
# Multi-stage build (concept — Abhinav implements)
FROM python:3.11-slim as builder
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as production
  # Non-root user for security
  RUN useradd --create-home appuser
  USER appuser
  COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
  COPY app/ ./app/
  EXPOSE 8000
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## 4. Deployment Pipeline (CI/CD)

### 4.1 GitHub Actions — CI (All Branches)

File: `.github/workflows/ci.yml`

```yaml
Trigger: push to any branch, pull_request to staging or main

Jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Set up Python 3.11
      - Install dependencies: pip install -r requirements.txt
      - Run unit tests: pytest tests/unit/ -v --tb=short
      - Upload test results as artifact

  security:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Install bandit: pip install bandit detect-secrets
      - Run bandit: bandit -r app/ -ll  (fail on HIGH+)
      - Run detect-secrets: detect-secrets scan --all-files --baseline .secrets.baseline
      - Fail if new secrets detected

  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    steps:
      - Checkout code
      - Build Docker image: docker build -t smvd-backend:${{ github.sha }} .
      - Run container smoke test: docker run --rm smvd-backend:<sha> python -c "from app.main import app; print('Import OK')"
```

### 4.2 GitHub Actions — Staging Deployment

File: `.github/workflows/staging.yml`

```yaml
Trigger: push to staging branch (merge from feature branch)

Jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - Checkout code
      - Set up Python 3.11
      - Install dependencies
      
      - Run migrations:
          Run: alembic upgrade head
          Env: DATABASE_URL=${{ secrets.STAGING_DATABASE_URL }}
          If this step fails: STOP, notify team, do NOT deploy app
      
      - Deploy to Railway:
          Use Railway CLI or GitHub integration
          Service: smvd-backend-staging
          Wait for deployment to complete
      
      - Health check:
          Run: curl -f https://staging-api.smvd.in/api/v1/health
          Retry: 3 times with 30 second delay
          If fails: ALERT team, rollback
      
      - Run smoke tests:
          Run: pytest tests/smoke/ -v  (lightweight integration checks)
      
      - Notify:
          Send message to team chat: "Staging deployed: {commit}"
```

### 4.3 GitHub Actions — Production Deployment

File: `.github/workflows/production.yml`

```yaml
Trigger: push to main branch (manual approval required)

Jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment: production    # Requires manual approval in GitHub Environments

    steps:
      - Checkout code
      - Install dependencies
      
      - BACKUP CONFIRMATION:
          Verify Supabase backup ran today (skip only if pre-confirmed)
      
      - Run migrations on production:
          Run: alembic upgrade head
          Env: DATABASE_URL=${{ secrets.PROD_DATABASE_URL }}
          If fails: STOP IMMEDIATELY. Notify team. Do NOT deploy.
      
      - Deploy to Railway production:
          Railway CLI deploy smvd-backend-production
          Strategy: Rolling deploy (Railway handles this)
      
      - Health check:
          Retry 5 times: curl -f https://api.smvd.in/api/v1/health
          If all retries fail: TRIGGER ROLLBACK
      
      - Post-deployment verification:
          Run: curl https://api.smvd.in/api/v1/services | python -c "import sys, json; data=json.load(sys.stdin); assert len(data)==10"
      
      - Tag release:
          git tag -a "v1.0.${BUILD_NUMBER}" -m "Production release"
          git push origin --tags
      
      - Notify:
          "Production deployed: {version}, {commit}"
```

### 4.4 Pipeline Diagram

```
Developer pushes to feature branch
            ↓
    CI runs (test + security + build)
            ↓
    PR opened → code review
            ↓
    PR merged to staging
            ↓
    CI runs again on staging
            ↓
    Migrations run on staging DB
            ↓
    Deploy to Railway staging
            ↓
    Health check + smoke tests
            ↓
    Manual QA on staging (Abhinav or Athreyan)
            ↓
    PR opened from staging → main
            ↓
    Manual approval in GitHub (Abhinav approves)
            ↓
    Migrations run on production DB
            ↓
    Deploy to Railway production (rolling)
            ↓
    Health check
            ↓
    Release tagged + team notified
```

### 4.5 GitHub Secrets Configuration

In GitHub repository → Settings → Secrets and Variables → Actions:

```
STAGING_DATABASE_URL
PROD_DATABASE_URL
RAILWAY_TOKEN
RAILWAY_STAGING_SERVICE_ID
RAILWAY_PROD_SERVICE_ID
SENTRY_DSN_STAGING
SENTRY_DSN_PROD
```

---

## 5. Monitoring and Logging

### 5.1 Health Check Endpoint

The `/api/v1/health` endpoint must verify:
```json
{
  "status": "ok",
  "environment": "production",
  "db": "connected",
  "version": "1.0.0",
  "timestamp": "2026-08-01T10:00:00Z"
}
```

If DB is unreachable, return:
```json
{ "status": "degraded", "db": "disconnected" }
```
with HTTP 503. This triggers Railway auto-restart.

### 5.2 UptimeRobot Setup

1. Go to https://uptimerobot.com
2. Create monitor:
   - Type: HTTP(S)
   - URL: `https://api.smvd.in/api/v1/health`
   - Interval: Every 5 minutes
   - Alert contact: Abhinav's email + WhatsApp
3. Create monitor for staging:
   - URL: `https://staging-api.smvd.in/api/v1/health`
   - Interval: Every 15 minutes

Alert conditions:
- Response code ≠ 200 → alert immediately
- Response time > 5000ms → alert
- 3 consecutive failures → call Abhinav's phone

### 5.3 Sentry Configuration

```python
# In app/main.py:
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,        # 10% of requests traced
        profiles_sample_rate=0.1,
        send_default_pii=False         # NEVER send PII to Sentry
    )
```

**Sentry Alert Rules:**
- New error → email immediately
- Error rate > 10/minute → email + Slack
- P0 error (booking failure) → immediate notification

**Sentry Filters (to reduce noise):**
- Ignore: 404 errors (user errors)
- Ignore: 401 errors (auth failures)
- Track: 500 errors (all)
- Track: Payment errors (all)
- Track: DB connection errors

### 5.4 Railway Logs

**Accessing Logs:**
```bash
# Via Railway CLI
railway logs -s smvd-backend-production --tail 100

# Via Railway Dashboard:
# Project → Service → Logs tab
# Filter by: ERROR or CRITICAL for error scanning
```

**Log Retention:** Railway retains logs for 7 days. For longer retention, export to a log aggregator.

### 5.5 Application Metrics to Monitor

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| API p95 latency | > 500ms | Investigate DB queries |
| DB connection pool usage | > 80% | Scale DB connections |
| Error rate | > 5% | Immediate investigation |
| Slot cleanup job | Not run in 15 min | Restart application |
| Payment webhook failures | Any | Immediate — check Razorpay |
| Railway memory | > 85% | Scale up RAM |
| Railway CPU | > 85% consistently | Scale up CPU |

### 5.6 Structured Log Format

All application logs are JSON (configured in `middleware/request_logging.py`):

```json
{
  "timestamp": "2026-08-01T10:30:00Z",
  "level": "INFO",
  "request_id": "uuid",
  "user_id": "uuid-or-null",
  "method": "POST",
  "path": "/api/v1/bookings",
  "status_code": 201,
  "duration_ms": 145,
  "ip": "1.2.3.4",
  "user_agent": "Mozilla/5.0",
  "message": "Booking created",
  "booking_id": "uuid"
}
```

---

## 6. Rollback Procedures

### 6.1 Railway Application Rollback

Railway keeps previous deployment snapshots. Rolling back is fast (< 1 minute):

```bash
# Via Railway CLI
railway rollback --service smvd-backend-production

# Via Railway Dashboard:
# Project → Service → Deployments tab
# Find previous successful deployment → "Rollback to this deployment"
```

### 6.2 Database Migration Rollback

> **Important:** Only roll back database migrations if the application code has also been rolled back. Running old app code with new schema can cause data corruption.

```bash
# Rollback one migration (most common)
alembic downgrade -1

# Rollback to specific migration
alembic downgrade 005_create_payments

# Rollback all migrations (DANGEROUS — data loss)
# DO NOT DO THIS IN PRODUCTION UNLESS ABSOLUTELY NECESSARY
alembic downgrade base
```

### 6.3 Rollback Decision Matrix

| Situation | Action |
|-----------|--------|
| App fails to start | Railway rollback immediately |
| App starts but health check fails | Railway rollback + check DB |
| App works but migration broke data | Fix forward (new migration), NOT rollback |
| Security vulnerability found | Railway rollback, patch, redeploy |
| Critical business logic bug | Railway rollback to last good deployment |

### 6.4 Migration Rollback Safety Rules

1. **Never roll back a migration that added data** without backing up that data first
2. **Never roll back on production without testing the rollback on staging first**
3. For every migration, write a tested downgrade function in the Alembic migration file
4. If downgrade function isn't possible (e.g., irreversible data transform) — create a new forward migration instead

### 6.5 Emergency Response Procedure

```
Incident detected (UptimeRobot alert or user report)
    ↓
Abhinav checks: curl https://api.smvd.in/api/v1/health
    ↓
If health check fails:
    → Railway rollback immediately
    → Verify health check passes
    → Notify team "Rolled back to previous version"
    ↓
If health check passes but business flow broken:
    → Check Railway logs: grep for ERROR
    → Check Sentry for the error
    → Identify the commit that introduced the bug
    → Hotfix or rollback based on severity
    ↓
Root cause analysis (within 24 hours):
    → Document what happened, why, how it was fixed
    → Add test to prevent recurrence
    → Update this document if procedure was insufficient
```

---

## 7. Backup Strategy

### 7.1 Supabase Pro Automatic Backups

**Supabase Pro plan includes:**
- Daily automated backups (Point-in-Time Recovery)
- 7-day backup retention (free tier: no backups)
- Manual snapshots (on-demand)

**Verify backup is active:**
1. Supabase Dashboard → Project → Settings → Database
2. Confirm "Point in Time Recovery" is enabled
3. Note the backup window time

### 7.2 Pre-Deployment Manual Snapshot

Before every production deployment:
```bash
# Via Supabase CLI — take a manual snapshot
supabase db dump -f backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Store in Supabase Storage private bucket: 'database-backups'
# OR store in secure cloud storage (Google Drive, S3)
```

This provides a known-good restore point immediately before any migration runs.

### 7.3 Backup Restoration Procedure

If data needs to be restored (last resort — data loss may occur):
```bash
# Step 1: Contact Supabase support (for PITR restoration)
# They can restore to any point in time within 7 days

# Step 2: If using manual dump backup
psql postgresql://postgres.[ref]:...@aws-0-ap-southeast-1.supabase.com:5432/postgres \
  < backups/backup_YYYYMMDD_HHMMSS.sql
```

### 7.4 Backup Retention Schedule

| Backup Type | Frequency | Retention | Where |
|-------------|-----------|-----------|-------|
| Supabase auto backup | Daily | 7 days | Supabase (managed) |
| Pre-deployment manual dump | Every deployment | 30 days | Supabase Storage (private bucket) |
| Monthly archive | 1st of each month | 1 year | Google Drive (encrypted) |

### 7.5 Backup Verification

Monthly: Test backup restoration on staging:
```bash
# Restore last week's backup to staging DB
# Verify all tables exist with correct data
# Delete the restored data from staging after verification
```

---

## 8. Production Checklist

Run this checklist on Day 14 before going live. Each item must be checked by the responsible developer.

### 8.1 Security

| Item | Owner | Status |
|------|-------|--------|
| No secrets in GitHub repository code | Abhinav | ☐ |
| All env vars set in Railway production (not empty) | Abhinav | ☐ |
| `.env` file confirmed not committed to Git | Abhinav | ☐ |
| `detect-secrets scan` shows zero findings | Abhinav | ☐ |
| `bandit -r app/` shows no HIGH/CRITICAL | Abhinav | ☐ |
| RLS enabled on all Supabase production tables | Abhinav | ☐ |
| `audit_logs` INSERT-only grant verified in production | Abhinav | ☐ |
| Admin accounts created with 2FA enabled | Athreyan | ☐ |
| Admin 2FA tested end-to-end in production | Athreyan | ☐ |
| CORS `ALLOWED_ORIGINS` has no wildcards | Abhinav | ☐ |
| CORS only allows `smvd.in` and `www.smvd.in` | Abhinav | ☐ |
| Rate limiting verified (OTP, login, bookings) | Abhinav | ☐ |
| Cloudflare WAF enabled for production domain | Abhinav | ☐ |
| Razorpay webhook HMAC verified end-to-end | Abhinav | ☐ |
| No 500 errors in first 10 min after deployment | Both | ☐ |

### 8.2 Database and Data

| Item | Owner | Status |
|------|-------|--------|
| All 11 migrations applied successfully | Athreyan | ☐ |
| All 10 services seeded with confirmed prices | Athreyan | ☐ |
| All conflict rules seeded | Athreyan | ☐ |
| Admin users created in `users` table | Athreyan | ☐ |
| `slot_inventory` table empty (slots created on demand) | Both | ☐ |
| Supabase Pro plan active (daily backups enabled) | Abhinav | ☐ |
| Pre-deployment backup snapshot taken | Abhinav | ☐ |
| Point-in-Time Recovery verified in dashboard | Abhinav | ☐ |

### 8.3 Business Rules Verification (Production)

| Item | Owner | Status |
|------|-------|--------|
| Kaapu + Kavasam conflict works | Abhinav | ☐ |
| Chariot session exclusivity works | Abhinav | ☐ |
| Thirukalyanam blocks morning chariot | Abhinav | ☐ |
| Ganapathy Homam + Chariot requires_approval=true | Abhinav | ☐ |
| Ganapathy Homam 5-day advance enforced | Abhinav | ☐ |
| Annadhanam Meals: 1 person only enforced | Abhinav | ☐ |
| E-Undiyal routes isolated from booking routes | Athreyan | ☐ |
| 80G certificate flow works (local preference) | Athreyan | ☐ |
| 80G certificate flow works (domestic + PAN) | Athreyan | ☐ |
| 80G certificate flow works (international) | Athreyan | ☐ |
| Donation minimum ₹100 enforced | Athreyan | ☐ |

### 8.4 Payment Integration

| Item | Owner | Status |
|------|-------|--------|
| Razorpay live keys configured (not test keys) | Abhinav | ☐ |
| Razorpay KYC complete (live account approved) | Abhinav | ☐ |
| Razorpay production webhook URL registered | Abhinav | ☐ |
| Razorpay webhook events: payment.captured + payment.failed | Abhinav | ☐ |
| Webhook HMAC secret matches production env var | Abhinav | ☐ |
| Payment order creation tested with live Razorpay | Abhinav | ☐ |
| Refund initiation tested | Abhinav | ☐ |

### 8.5 Infrastructure and Deployment

| Item | Owner | Status |
|------|-------|--------|
| Railway production service deployed | Abhinav | ☐ |
| Custom domain `api.smvd.in` resolves correctly | Abhinav | ☐ |
| HTTPS working (no HTTP access) | Abhinav | ☐ |
| Health check returns 200 | Abhinav | ☐ |
| CI/CD pipeline tested with a real deployment | Abhinav | ☐ |
| Rollback procedure tested (rolled back staging, verified it worked) | Abhinav | ☐ |

### 8.6 Monitoring and Operations

| Item | Owner | Status |
|------|-------|--------|
| UptimeRobot monitor active (5 min interval) | Abhinav | ☐ |
| UptimeRobot alert email configured (Abhinav) | Abhinav | ☐ |
| Sentry configured for production | Abhinav | ☐ |
| Sentry test event verified received | Abhinav | ☐ |
| APScheduler jobs visible in startup logs | Abhinav | ☐ |
| `slot_cleanup` job runs every 5 minutes | Abhinav | ☐ |
| `notice_scheduler` job runs every 5 minutes | Both | ☐ |
| Railway logs accessible and readable | Both | ☐ |
| No ERROR or CRITICAL logs in first 10 minutes | Both | ☐ |

### 8.7 API Functionality (Production Smoke Test)

Run these manually after deployment:

```bash
# 1. Health check
curl https://api.smvd.in/api/v1/health
# Expected: {"status":"ok"}

# 2. Services
curl https://api.smvd.in/api/v1/services | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} services found')"
# Expected: 10 services found

# 3. Notices (should be empty initially)
curl https://api.smvd.in/api/v1/notices
# Expected: []

# 4. Admin dashboard (requires admin JWT)
curl -H "Authorization: Bearer <admin_token>" https://api.smvd.in/admin/reports/dashboard
# Expected: KPI object

# 5. OTP send (with real phone number)
curl -X POST https://api.smvd.in/api/v1/auth/otp/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "+91XXXXXXXXXX"}'
# Expected: {"message": "OTP sent successfully"}
# Verify OTP arrives on the phone
```

### 8.8 Load Test Results Sign-off

| Test | p95 Latency | Error Rate | Zero Overbooking | Pass |
|------|------------|------------|-----------------|------|
| Availability (200 users) | < 150ms | < 0.1% | N/A | ☐ |
| Booking (50 users) | < 300ms | < 1% | N/A | ☐ |
| Overbooking (100 users, cap=5) | — | — | Exactly 5 | ☐ |
| Webhook (30 users) | < 200ms | 0% | N/A | ☐ |
| Mixed load (100 users, 10 min) | < 300ms | < 1% | Verified | ☐ |

**Load test sign-off by:** Abhinav _____________ Date: _________

### 8.9 Final Go/No-Go Decision

Before Go-Live, all **critical items** must be ✅:
- [ ] Zero overbooking test passed
- [ ] Security checks all passed (bandit, detect-secrets, CORS, rate limits, RLS)
- [ ] Payment flow works end-to-end in production
- [ ] Admin 2FA works
- [ ] Supabase Pro backup confirmed
- [ ] UptimeRobot and Sentry configured

**GO-LIVE APPROVED BY:**  
Abhinav: _________________ Date: _________  
Athreyan: ________________ Date: _________

---

*This deployment plan must be reviewed and updated after each major change to infrastructure or dependencies.*  
*Questions about deployment → Abhinav (Tech Lead)*
