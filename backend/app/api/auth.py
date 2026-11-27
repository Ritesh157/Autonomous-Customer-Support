"""Demo auth routes (P3-2, N1).

POST /api/v1/auth/login  — issues an 8-hour JWT for the three demo users.
GET  /api/v1/auth/me     — returns the current user from their Bearer token.

Login is guarded by ``DEMO_MODE``: the route returns 403 in production so this
endpoint can never be used as a backdoor once a real auth provider is wired up.
The demo password is the literal string ``"demo"`` for all three users; it is
intentionally not configurable — if you need a real auth provider, disable
DEMO_MODE and wire Supabase or another identity platform.

No service-role secret or JWT_SECRET value is ever returned to the client.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import session_scope
from app.core.security import CurrentUser, create_token, get_current_user
from app.repositories.customers import ProfileRepository
from app.schemas.common import Role

router = APIRouter(prefix="/auth", tags=["auth"])

_DEMO_PASSWORD = "demo"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    sub: str
    email: str
    role: Role
    full_name: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _lookup_profile(session: AsyncSession, email: str) -> UserOut | None:
    profile = await ProfileRepository(session).get_by_email(email)
    if profile is None:
        return None
    return UserOut(
        sub=profile.id,
        email=profile.email,
        role=Role(profile.role),
        full_name=profile.full_name,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Issue an 8-hour JWT for a demo user.

    Only available when ``DEMO_MODE=true``. Password for all demo users is
    the literal string ``demo``.
    """
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is disabled outside DEMO_MODE",
        )
    if body.password != _DEMO_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    async with session_scope() as session:
        user_out = await _lookup_profile(session, body.email)
    if user_out is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_token(user_out.email, user_out.role, sub=user_out.sub)
    return LoginResponse(token=token, user=user_out)


@router.get("/me", response_model=UserOut)
async def me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> UserOut:
    """Return the caller's identity from their Bearer token.

    The profile ``full_name`` is re-fetched from the database so it reflects
    the current value even if the token was issued before a name change.
    """
    async with session_scope() as session:
        user_out = await _lookup_profile(session, current_user.email)
    if user_out is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return user_out
