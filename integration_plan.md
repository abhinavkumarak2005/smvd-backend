# Sri Manakula Vinayagar Devasthanam — Integration Plan

**Project:** Temple Booking Platform Backend  
**Team:** Abhinav (Lead) · Athreyan  
**Duration:** 14 Days  

---

## Table of Contents

1. [Git Branching Strategy](#1-git-branching-strategy)
2. [Pull Request Workflow](#2-pull-request-workflow)
3. [Code Review Process](#3-code-review-process)
4. [Merge Workflow](#4-merge-workflow)
5. [Migration Workflow](#5-migration-workflow)
6. [Environment Synchronization](#6-environment-synchronization)
7. [Daily Development Workflow](#7-daily-development-workflow)
8. [Conflict Prevention Strategy](#8-conflict-prevention-strategy)
9. [Shared Utilities Contract](#9-shared-utilities-contract)
10. [Communication Protocol](#10-communication-protocol)

---

## 1. Git Branching Strategy

### Branch Hierarchy

```
main (production)
  └── staging (staging environment)
        └── feature/abhinav-*  (Abhinav's features)
        └── feature/athreyan-* (Athreyan's features)
        └── fix/abhinav-*
        └── fix/athreyan-*
```

### Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/{owner}-{feature-name}` | `feature/abhinav-booking-engine` |
| Bug Fix | `fix/{owner}-{issue-description}` | `fix/athreyan-notice-scheduler` |
| Migration | `migration/{description}` | `migration/add-certificate-columns` |
| Hotfix | `hotfix/{description}` | `hotfix/webhook-hmac-verify` |
| Release | `release/v{major}.{minor}` | `release/v1.0` |

### Rules

- **Never commit directly to `main` or `staging`** — all changes via PR
- `main` branch = production code — protected, requires 1 approval + all CI checks passing
- `staging` branch = staging code — protected, requires 1 approval
- Feature branches are created from `staging`, not `main`
- Feature branch name must include owner (`abhinav` or `athreyan`) — prevents naming conflicts
- Delete feature branch after PR is merged

### Branch Lifecycle

```
1. git checkout staging
2. git pull origin staging
3. git checkout -b feature/abhinav-booking-engine
4. [develop, commit]
5. git push origin feature/abhinav-booking-engine
6. Open PR → staging
7. Review → Approve → Merge (squash)
8. Delete feature branch
```

---

## 2. Pull Request Workflow

### PR Title Format

```
[SCOPE] Brief description

Examples:
[AUTH] Implement OTP send and verify endpoints
[BOOKING] Add conflict rules engine for Kaapu/Kavasam
[EUNDIYAL] 80G certificate delivery preference logic
[ADMIN] Booking approval and rejection endpoints
[NOTICE] Notice lifecycle scheduler
[TEST] Unit tests for payment webhook handler
[FIX] Slot pending count not decrementing on payment failure
[DEPLOY] Dockerfile and GitHub Actions CI pipeline
[MIGRATION] Add 80G certificate columns to e_undiyal_transactions
```

### PR Description Template

Every PR must include this description:

```markdown
## What this PR does
Brief description of the change.

## Modules changed
- app/services/booking_engine.py
- app/repositories/slot_repo.py

## Type of change
- [ ] New feature
- [ ] Bug fix
- [ ] Migration
- [ ] Tests only
- [ ] Refactor

## How to test
1. Step 1
2. Step 2

## Checklist
- [ ] Code follows project conventions (no hardcoded IDs, no f-strings in SQL)
- [ ] No secrets committed to code
- [ ] Audit log written for all write operations
- [ ] Tests added/updated for this change
- [ ] Migration included if schema changed (run `alembic upgrade head`)
- [ ] `detect-secrets scan` shows zero new secrets
```

### PR Size Guidelines

| Size | Lines Changed | Review Time |
|------|--------------|-------------|
| Small | < 100 | < 30 min |
| Medium | 100–300 | 30–60 min |
| Large | 300–600 | 60–90 min |
| Too Large | > 600 | Must be split into smaller PRs |

**Split large PRs** — if your feature is large, open multiple small PRs in sequence. Example:
- PR 1: `[BOOKING] Booking repository and slot repository`
- PR 2: `[BOOKING] Calendar service and booking engine core`
- PR 3: `[BOOKING] Conflict checker integration`

---

## 3. Code Review Process

### Who Reviews What

| Author | Reviewer |
|--------|---------|
| Abhinav | Athreyan reviews |
| Athreyan | Abhinav reviews |

Both developers review each other's work. The author may not merge their own PR.

### Review Timeline

- PR must be reviewed within **4 hours** of being opened during working hours
- If reviewer is unavailable, notify via chat and agree on review time
- Emergency fixes (`hotfix/`) can be self-merged with async review afterward

### What Reviewers Must Check

**Business Logic:**
- [ ] Is the booking engine transaction complete and atomic?
- [ ] Does slot_service always use FOR UPDATE? (No writes without lock)
- [ ] Is E-Undiyal completely isolated from booking tables?
- [ ] Are all conflict rules enforced from DB (not hardcoded)?
- [ ] Does audit_service get called for every write?

**Security:**
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] No string interpolation in SQL queries (only parameterized: `$1, $2`)
- [ ] JWT verification present on all protected routes
- [ ] Role guard matches the correct minimum role
- [ ] Webhook HMAC verified before any processing

**Code Quality:**
- [ ] Error messages are user-friendly (no stack traces in responses)
- [ ] Error codes are machine-readable (e.g., `SLOT_FULL`, `DATE_BLOCKED`)
- [ ] All functions have single responsibility
- [ ] No business logic in repositories
- [ ] No SQL in services (only repository calls)

**Tests:**
- [ ] New feature has corresponding test
- [ ] Edge cases covered (empty list, null values, capacity=0)
- [ ] Mocked external calls (Razorpay, Supabase Auth, SMS)

### Commenting Standards

| Prefix | Meaning |
|--------|---------|
| `MUST:` | Blocking — must be fixed before merge |
| `SHOULD:` | Important but not blocking |
| `SUGGEST:` | Optional improvement |
| `QUESTION:` | Needs clarification |

Example:
```
MUST: This SQL query uses string interpolation — SQL injection risk.
      Change to parameterized query with $1, $2.

SHOULD: This function is doing too much — extract the calendar check 
        to calendar_service.

SUGGEST: Consider adding a type hint for the return value here.
```

### Approval and Merge

- 1 approval required (from the other developer)
- All CI checks must pass (pytest, bandit, detect-secrets)
- No unresolved `MUST:` comments
- Author resolves all comments, then re-requests review

---

## 4. Merge Workflow

### Merge Strategy: Squash Merge

All PRs are merged using **squash merge** into staging:
- All commits in the feature branch are squashed into 1 commit
- The final commit message is the PR title
- Keeps staging branch history clean and readable

### Merge Sequence for Related PRs

When Athreyan's work depends on Abhinav's (or vice versa), follow this order:

```
Day 1:
  Abhinav: feature/abhinav-project-setup → staging (merged first)
  Athreyan: migration/all-tables → staging (merged after Abhinav's setup)

Day 3:
  Athreyan: feature/athreyan-service-schemas → staging (merged first)
  Abhinav: feature/abhinav-booking-engine → staging (merged after)
  (Abhinav imports Athreyan's schemas — must wait)
```

### Merge Freeze Periods

| Period | Rule |
|--------|------|
| Day 13 staging deploy | No merges to staging after 5 PM |
| Day 14 production deploy | No merges to main after 3 PM |
| During load test | No deployments |

---

## 5. Migration Workflow

### Rules

- **Athreyan owns all migration files** — only Athreyan creates new Alembic migrations
- Abhinav may request migrations by describing the schema change needed
- Migration files are reviewed in the same PR as the feature that requires them
- Migrations are **never merged to staging or production without testing locally first**

### Migration Creation Process

```bash
# Step 1: Athreyan writes the migration (or modifies existing)
# Step 2: Test locally
alembic upgrade head
alembic downgrade -1   # test rollback
alembic upgrade head   # verify re-apply works

# Step 3: Verify tables in Supabase dashboard
# Step 4: Commit migration + test result
git add migrations/versions/xxx_new_migration.py
git commit -m "[MIGRATION] Add certificate columns to e_undiyal_transactions"
```

### Migration File Naming

```
{number}_{description}.py

Examples:
001_create_users.py
002_create_services.py
011_seed_services_conflict_rules.py
012_add_certificate_columns.py
```

### Migration Deployment Process

```
Local Dev:
  alembic upgrade head   (automatic on app startup — not for production)

Staging:
  GitHub Actions runs: alembic upgrade head (before Railway deploy)
  If migration fails → deployment stops, no app deploy

Production:
  GitHub Actions runs: alembic upgrade head (before Railway deploy)
  If migration fails → deployment stops immediately
  Run alembic downgrade -1 to rollback
  Fix migration, re-deploy
```

### Dangerous Migration Rules

- **Never use `alembic downgrade base`** in staging/production
- **Never drop a column** without a 2-step migration:
  - Step 1: Stop writing to the column (deploy)
  - Step 2: Drop the column (next deploy)
- **Never rename a column** — add new column + migrate data + drop old
- Before any destructive migration: notify the other developer and take a manual DB snapshot

---

## 6. Environment Synchronization

### Three Environments

| Env | Branch | DB | Purpose | Who has access |
|-----|--------|-----|---------|----------------|
| Local | feature/* | Supabase Dev | Development | Both devs |
| Staging | staging | Supabase Staging | QA + pre-release | Both devs |
| Production | main | Supabase Prod | Live users | Abhinav (deploy), Athreyan (read audit) |

### Keeping Local in Sync with Staging

Every morning before starting work:
```bash
git checkout staging
git pull origin staging
git checkout feature/my-feature
git rebase staging    # keep feature branch up to date
```

### Environment Variables Synchronization

All env vars are maintained in a **shared private document** (Notion/Google Doc — not in Git).

Format:
```
VARIABLE_NAME=                 # Required
VARIABLE_NAME=value            # Same across all envs
VARIABLE_NAME=<dev-value>      # Different per env
```

When a new env var is added:
1. Add it to `.env.example` with placeholder value
2. Add it to the private env vars document with actual values per environment
3. Update Railway environment variables for staging AND production
4. Notify the other developer

### Database Sync

- Never copy production data to local dev (PII concern)
- Staging DB is seeded with the same seed data as production (from migration 011)
- If staging DB is corrupted: `alembic downgrade base` → `alembic upgrade head` (re-seeds)
- Production DB is never reset — use rollback procedures if needed

---

## 7. Daily Development Workflow

### Both Developers — Daily Schedule

```
09:00 — Daily sync (15 minutes, mandatory)
  Abhinav: What did I complete yesterday? What am I doing today? Any blockers?
  Athreyan: Same. Surface any dependency conflicts early.

09:15 — Development work begins
  
12:00 — Midday check (5 minutes)
  Quick status via chat: "PR opened/merged", "blocked on X"

17:00 — End of day
  All code committed (even if incomplete — push to feature branch)
  Open PR if feature is ready for review
  Update personal task checklist

17:30 — Review partner's PR (if opened)
  Complete review before end of day
```

### Abhinav's Daily Pattern

```
09:00 - Pull latest staging
09:15 - Create feature branch for the day's work
      - Implement feature
      - Test manually with curl/Postman
      - Write tests
17:00 - Push to GitHub, open PR, notify Athreyan
17:30 - Review Athreyan's PR
```

### Athreyan's Daily Pattern

```
09:00 - Pull latest staging
09:15 - Check if Abhinav has merged any shared files (schemas, etc.)
      - Create feature branch
      - Implement feature
      - Test manually
17:00 - Push to GitHub, open PR, notify Abhinav
17:30 - Review Abhinav's PR
```

### PR Review Rotation

- Abhinav opens PR → Athreyan reviews
- Athreyan opens PR → Abhinav reviews
- Both developers approve before any merge to `main`

### End-of-Day Commit Policy

Even if a feature is incomplete, push the work-in-progress to GitHub:
```bash
git add .
git commit -m "WIP: [BOOKING] booking engine step 5-7 - incomplete"
git push origin feature/abhinav-booking-engine
```

This ensures no work is lost and the other developer can see progress.

---

## 8. Conflict Prevention Strategy

### File Ownership (No Conflicts by Design)

Modules are divided so each developer owns specific files exclusively:

| File/Folder | Owner | Never Touched By |
|------------|-------|-----------------|
| `app/services/booking_engine.py` | Abhinav | Athreyan |
| `app/services/conflict_checker.py` | Abhinav | Athreyan |
| `app/services/slot_service.py` | Abhinav | Athreyan |
| `app/services/payment_service.py` | Abhinav | Athreyan |
| `app/services/webhook_service.py` | Abhinav | Athreyan |
| `app/services/calendar_service.py` | Abhinav | Athreyan |
| `app/services/e_undiyal_service.py` | Athreyan | Abhinav |
| `app/services/certificate_service.py` | Athreyan | Abhinav |
| `app/services/notice_service.py` | Athreyan | Abhinav |
| `app/services/report_service.py` | Athreyan | Abhinav |
| `app/routers/bookings/` | Abhinav | Athreyan |
| `app/routers/payments/` | Abhinav | Athreyan |
| `app/routers/auth/` | Abhinav | Athreyan |
| `app/routers/e_undiyal/` | Athreyan | Abhinav |
| `app/routers/admin/notices.py` | Athreyan | Abhinav |
| `app/routers/admin/users.py` | Athreyan | Abhinav |
| `app/routers/admin/reports.py` | Athreyan | Abhinav |
| `app/routers/admin/bookings.py` | Athreyan | Abhinav |
| `app/routers/admin/services.py` | Athreyan | Abhinav |
| `migrations/` | Athreyan | Abhinav |
| `app/main.py` | **Shared** — coordinate before editing |

### Shared Files Protocol

`app/main.py` is the only shared file. Rule:
- Only one developer edits it at a time
- Notify via chat: "Editing main.py — please don't touch for 10 minutes"
- Changes: add `include_router(...)` lines at the bottom of startup section
- Always pull latest before editing main.py

### Resolving Merge Conflicts (if they occur)

```bash
# 1. Update feature branch
git checkout feature/my-branch
git rebase staging

# 2. If conflict:
git status    # see conflicted files
# Edit files to resolve conflicts — preserve BOTH changes, not just yours
git add <resolved-files>
git rebase --continue

# 3. If confused:
git rebase --abort    # start over
# Ask the other developer to walk through it together
```

---

## 9. Shared Utilities Contract

These shared modules must be finalized by Day 2 and not changed afterward without coordinating:

### audit_service.py (Abhinav writes, Athreyan calls)

```python
# Contract:
audit_service.write_log(
    action: str,           # e.g. "booking.created"
    entity_type: str,      # e.g. "booking", "payment", "notice"
    entity_id: UUID | None,
    actor_id: UUID | None, # current_user.id, or None for system
    before_state: dict | None,
    after_state: dict | None,
    ip_address: str | None,
    user_agent: str | None
) -> None

# Always call as:
background_tasks.add_task(audit_service.write_log, ...)
# Never: await audit_service.write_log(...)
```

### notification_service.py (Abhinav writes, Athreyan calls)

```python
# Contract:
notification_service.send_sms(phone: str, message: str) -> None
notification_service.send_email(to: str, subject: str, html_body: str) -> None

# Always call as BackgroundTask (fire-and-forget):
background_tasks.add_task(notification_service.send_sms, phone, message)
# Never: await notification_service.send_sms(...)
```

### payment_service.py (Abhinav writes, Athreyan calls for E-Undiyal)

```python
# Contract:
payment_service.create_order(entity_id: UUID, amount_paise: int) -> PaymentOrderResult
# entity_id can be booking_id or e_undiyal_transaction_id

# Returns:
PaymentOrderResult(gateway_order_id: str, amount_paise: int, currency: str)
```

### dependencies/auth.py (Abhinav writes, both use)

```python
# Contract:
require_role("devotee")       # minimum role: devotee
require_role("staff")         # minimum role: staff
require_role("admin")         # minimum role: admin
require_role("super_admin")   # only super_admin

# Usage in router:
@router.post("/endpoint")
async def my_endpoint(
    current_user: CurrentUser = Depends(require_role("admin"))
):
    ...
```

---

## 10. Communication Protocol

### Daily Sync Structure (15 min max)

```
1. Yesterday (2 min each): What was completed? Any incomplete items?
2. Today (2 min each): What's the plan for today?
3. Blockers (5 min): Any dependency issues? Need to sync on shared files?
4. PRs (1 min): Any PRs pending review?
```

### Chat Conventions

Use these prefixes in messages:
- `[BLOCKER]` — I am blocked and need immediate help
- `[PR READY]` — New PR opened, please review when ready
- `[MERGED]` — PR merged to staging, shared files updated
- `[HEADS UP]` — FYI, making a change that affects shared code
- `[QUESTION]` — Non-urgent question

### Escalation

If blocked for > 30 minutes:
1. Post `[BLOCKER]` in chat
2. 15-minute pair programming session to resolve
3. If still blocked → document the issue, move to next task, return to blocker later

### Documenting Decisions

Any significant technical decision made during the sprint must be documented as a GitHub PR comment on the relevant PR. Examples:
- "Decided to use HMAC-SHA256 instead of RSA for webhook verification because Razorpay only supports HMAC"
- "Changed slot capacity check from application to DB level — here's why..."

This creates a traceable history of why decisions were made.
