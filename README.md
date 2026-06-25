# smvd-backend

FastAPI backend for the **Sri Manakula Vinayagar Devasthanam** temple booking and operations platform.

## Stack

- **Runtime:** Python 3.11 + FastAPI
- **Database:** Supabase PostgreSQL via asyncpg
- **Auth:** Supabase Auth (OTP + Admin 2FA)
- **Payments:** Razorpay
- **Deployment:** Railway

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/smvd-backend.git
cd smvd-backend

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with real values (get from Abhinav)

# 5. Run the server
uvicorn app.main:app --reload
```

## Health Check

```
GET http://localhost:8000/api/v1/health
```

## Team

| Developer | Role | Days |
|-----------|------|------|
| Abhinav | Tech Lead / Core Backend | Day 1–14 |
| Athreyan | Backend Developer | Day 1–14 |

## Reference Docs

- `abhinav_backend_tasks.md` — Abhinav's task list
- `athreyan_backend_tasks.md` — Athreyan's task list
- `backend_master_plan.md` — Full architecture and plan
- `backend_architecture.md` — Detailed technical architecture
