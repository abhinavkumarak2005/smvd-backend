from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import asyncpg

from app.config import get_settings
from app.database import get_db

settings = get_settings()
_bearer = HTTPBearer()

# Role hierarchy — higher number = more permissions
ROLE_HIERARCHY: dict[str, int] = {
    "devotee": 1,
    "staff": 2,
    "admin": 3,
    "super_admin": 4,
}


@dataclass
class CurrentUser:
    id: str
    role: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    conn: asyncpg.Connection = Depends(get_db),
) -> CurrentUser:
    """Verify Supabase JWT and return the authenticated user."""
    token = credentials.credentials
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError:
        raise exc

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise exc

    # Look up role from users table (source of truth)
    row = await conn.fetchrow(
        "SELECT id, role, is_active FROM users WHERE id = $1",
        user_id,
    )
    if row is None:
        raise exc
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return CurrentUser(id=str(row["id"]), role=row["role"])


def require_role(minimum_role: str):
    """
    Dependency factory — use as: Depends(require_role("admin"))
    Raises 403 if the authenticated user's role is below minimum_role.
    """
    async def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if ROLE_HIERARCHY.get(current_user.role, 0) < ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return dependency


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    conn: asyncpg.Connection = Depends(get_db),
) -> CurrentUser | None:
    """Returns CurrentUser if a valid Bearer token is present, otherwise None (guest)."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        row = await conn.fetchrow(
            "SELECT id, role, is_active FROM users WHERE id = $1", user_id
        )
        if row and row["is_active"]:
            return CurrentUser(id=str(row["id"]), role=row["role"])
    except JWTError:
        pass
    return None

