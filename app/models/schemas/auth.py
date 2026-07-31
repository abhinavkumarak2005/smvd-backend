import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator


_E164 = re.compile(r"^\+[1-9]\d{1,14}$")


class OTPSendRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _E164.match(v):
            raise ValueError("Phone must be in E.164 format e.g. +919876543210")
        return v


class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminVerify2FARequest(BaseModel):
    session_token: str
    totp_code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserProfile(BaseModel):
    id: UUID
    phone: str | None
    email: str | None
    role: str
    created_at: datetime
