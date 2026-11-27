"""N2: fixed-window rate limiter backed by Redis / fakeredis.

Window: 60 seconds. Limit: ``settings.rate_limit_per_minute``.
Client key: first IP from ``X-Forwarded-For``, or the ASGI ``scope["client"]``
host, or ``"unknown"`` as a last resort.

Returns 429 with a ``Retry-After: 60`` header when the client exceeds the
limit. If Redis is unavailable the middleware fails **open** (request is
allowed) so a Redis outage never takes the whole API down.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.redis import get_redis
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 60


def _client_key(scope: Scope) -> str:
    """Extract the best available client identifier for rate-limit bucketing."""
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            first_ip = value.decode("latin-1").split(",")[0].strip()
            if first_ip:
                return first_ip
    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


async def _check(redis, key: str, limit: int) -> tuple[bool, int]:
    """Atomically increment the counter and set TTL on the first hit.

    Returns ``(allowed, current_count)``.
    """
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _WINDOW_SECONDS)
    return count <= limit, count


class RateLimitMiddleware:
    """Pure ASGI rate-limit middleware (N2, CLAUDE.md §9)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.redis = get_redis()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        limit = settings.rate_limit_per_minute
        key = f"ratelimit:{_client_key(scope)}"

        try:
            allowed, _count = await _check(self.redis, key, limit)
        except Exception:
            logger.warning("rate-limit Redis check failed — failing open", exc_info=True)
            allowed = True

        if not allowed:
            response = JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
