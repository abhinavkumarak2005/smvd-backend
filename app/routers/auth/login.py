from datetime import datetime, timedelta, timezone

import httpx
import pyotp
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
import asyncpg

from app.config import get_settings
from app.database import get_db
from app.models.schemas.auth import AdminLoginRequest, AdminVerify2FARequest, LoginRequest, UserProfile

router = APIRouter(tags=["Auth — Admin"])
settings = get_settings()

_AUTH_URL = f"{settings.SUPABASE_URL}/auth/v1"
_HEADERS = {"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"}

# Pre-2FA token expires in 5 minutes, signed with our JWT secret
_PRE2FA_TTL = 5
_PRE2FA_TYPE = "pre_2fa"


def _make_pre2fa_token(user_id: str, access_token: str, refresh_token: str) -> str:
    payload = {
        "sub": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "type": _PRE2FA_TYPE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_PRE2FA_TTL),
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def _decode_pre2fa_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    if payload.get("type") != _PRE2FA_TYPE:
        raise HTTPException(status_code=401, detail="Invalid session token type")
    return payload


@router.post("/admin/login")
async def admin_login(
    body: AdminLoginRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Step 1 of admin auth — email/password → pre-2FA session token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AUTH_URL}/token?grant_type=password",
            json={"email": body.email, "password": body.password},
            headers=_HEADERS,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    data = resp.json()
    supabase_user = data["user"]
    user_id = supabase_user["id"]

    # Verify role from our users table
    row = await conn.fetchrow(
        "SELECT role, totp_enabled FROM users WHERE id = $1 AND is_active = TRUE",
        user_id,
    )
    if row is None or row["role"] not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    session_token = _make_pre2fa_token(user_id, data["access_token"], data["refresh_token"])
    return {"session_token": session_token, "message": "Enter your TOTP code"}


@router.post("/admin/verify-2fa")
async def verify_2fa(
    body: AdminVerify2FARequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Step 2 of admin auth — validate TOTP code → return full JWT."""
    payload = _decode_pre2fa_token(body.session_token)
    user_id = payload["sub"]

    row = await conn.fetchrow(
        "SELECT totp_secret, totp_enabled FROM users WHERE id = $1",
        user_id,
    )
    if row is None or not row["totp_enabled"] or not row["totp_secret"]:
        raise HTTPException(status_code=403, detail="2FA not configured for this account")

    if not pyotp.TOTP(row["totp_secret"]).verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    return {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Exchange a refresh token for a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AUTH_URL}/token?grant_type=refresh_token",
            json={"refresh_token": refresh_token},
            headers=_HEADERS,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    data = resp.json()
    return {"access_token": data["access_token"], "refresh_token": data["refresh_token"]}


@router.post("/login")
async def login(
    body: LoginRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Public auth — email/password -> full JWT."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AUTH_URL}/token?grant_type=password",
            json={"email": body.email, "password": body.password},
            headers=_HEADERS,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    data = resp.json()
    supabase_user = data["user"]
    user_id = supabase_user["id"]

    row = await conn.fetchrow(
        "SELECT id, phone, email, role, created_at FROM users WHERE id = $1 AND is_active = TRUE",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=401, detail="User account disabled or not found")

    profile = UserProfile(
        id=row["id"],
        phone=row["phone"],
        email=row["email"],
        role=row["role"],
        created_at=row["created_at"],
    )

    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": profile,
    }

