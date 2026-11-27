"""JWT authentication and RBAC for CloudDesk (N1, CLAUDE.md §2).

Role hierarchy: viewer=1 < agent=2 < admin=3.
All tokens are HS256-signed with ``settings.effective_jwt_secret``.
Demo tokens expire in 8 hours.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas.common import Role

_ROLE_LEVEL: dict[Role, int] = {Role.VIEWER: 1, Role.AGENT: 2, Role.ADMIN: 3}
_ALGORITHM = "HS256"
_DEMO_TTL_HOURS = 8

_bearer = HTTPBearer(auto_error=True)


class CurrentUser(BaseModel):
    sub: str
    email: str
    role: Role


def create_token(
    email: str,
    role: Role,
    sub: str | None = None,
    ttl_hours: int = _DEMO_TTL_HOURS,
) -> str:
    """Issue a signed JWT for the given identity. Used by demo auth routes (P3-2)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict = {
        "sub": sub or email,
        "email": email,
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(hours=ttl_hours),
    }
    return jwt.encode(payload, settings.effective_jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> CurrentUser:
    """Verify signature and expiry; raise 401 on any failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.effective_jwt_secret, algorithms=[_ALGORITHM])
        return CurrentUser(
            sub=payload["sub"],
            email=payload["email"],
            role=Role(payload["role"]),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> CurrentUser:
    """FastAPI dependency: decode Bearer token → ``CurrentUser``."""
    return decode_token(credentials.credentials)


def require_role(minimum: Role):
    """Dependency factory: inject ``CurrentUser`` and enforce a minimum role level.

    Usage::

        @router.post("/tickets/{id}/run")
        async def run(user: Annotated[CurrentUser, Depends(require_role(Role.AGENT))]):
            ...
    """
    min_level = _ROLE_LEVEL[minimum]

    def _dep(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if _ROLE_LEVEL[user.role] < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' insufficient; requires '{minimum}'",
            )
        return user

    return _dep
