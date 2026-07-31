from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
import asyncpg

from app.config import get_settings
from app.database import get_db
from app.models.schemas.auth import OTPSendRequest, OTPVerifyRequest, UserProfile

router = APIRouter(tags=["Auth — OTP"])
settings = get_settings()

_AUTH_URL = f"{settings.SUPABASE_URL}/auth/v1"
_HEADERS = {"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"}


@router.post("/otp/send")
async def send_otp(body: OTPSendRequest, request: Request):
    """Send OTP to phone via Supabase Auth (rate limited: 3/10min per IP)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AUTH_URL}/otp",
            json={"phone": body.phone, "channel": "sms"},
            headers=_HEADERS,
        )
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("msg", "Failed to send OTP"))
    return {"message": "OTP sent successfully"}


@router.post("/otp/verify")
async def verify_otp(
    body: OTPVerifyRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Verify OTP, upsert user into users table, return JWT tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AUTH_URL}/verify",
            json={"type": "sms", "phone": body.phone, "token": body.otp},
            headers=_HEADERS,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid OTP")

    data = resp.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    supabase_user = data["user"]
    user_id = supabase_user["id"]
    phone = supabase_user.get("phone")

    # Upsert into our users table
    row = await conn.fetchrow(
        """
        INSERT INTO users (id, phone, role)
        VALUES ($1, $2, 'devotee')
        ON CONFLICT (id) DO UPDATE SET phone = EXCLUDED.phone
        RETURNING id, phone, email, role, created_at
        """,
        user_id, phone,
    )

    profile = UserProfile(
        id=row["id"],
        phone=row["phone"],
        email=row["email"],
        role=row["role"],
        created_at=row["created_at"],
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "profile": profile}
