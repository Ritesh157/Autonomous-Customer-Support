"""N6: audit log — every non-GET request is recorded in ``audit_logs``.

The middleware:
  - skips GET and non-HTTP events (WebSocket, lifespan).
  - tries to identify the caller from the ``Authorization: Bearer …`` header;
    falls back to ``"anonymous"`` if the token is absent or invalid.
  - captures the HTTP status code by wrapping ``send``.
  - writes one ``audit_logs`` row **after** the response has been sent so that
    telemetry never slows down or breaks the actual response.
  - never raises — a failed write is logged as a warning and swallowed.
"""

from __future__ import annotations

import logging
import re

from app.core.database import session_scope
from app.core.security import decode_token
from app.repositories.audit import AuditRepository
from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

_API_PATH = re.compile(r"^/api/v\d+/([^/]+)(?:/([^/?#]+))?")


def _extract_resource(path: str) -> tuple[str, str]:
    """Return ``(resource_type, resource_id)`` from an API path.

    ``/api/v1/tickets/CD-1002/run`` → ``("tickets", "CD-1002")``
    ``/api/v1/auth/login``         → ``("auth", "")``
    ``/health``                    → ``("", "")``
    """
    m = _API_PATH.match(path)
    if not m:
        return "", ""
    return m.group(1) or "", m.group(2) or ""


def _extract_actor(headers: list[tuple[bytes, bytes]]) -> str:
    """Return the caller's email from the Bearer token, or ``"anonymous"``."""
    for name, value in headers:
        if name == b"authorization":
            raw = value.decode("latin-1")
            if raw.startswith("Bearer "):
                try:
                    user = decode_token(raw[7:])
                    return user.email
                except HTTPException:
                    pass
            break
    return "anonymous"


class AuditMiddleware:
    """Pure ASGI middleware that appends one row to ``audit_logs`` per non-GET request (N6)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        if method == "GET":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        request_id: str = scope.get("state", {}).get("request_id", "")

        actor = _extract_actor(headers)
        resource_type, resource_id = _extract_resource(path)
        status_code: int = 0

        async def _send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        await self.app(scope, receive, _send_wrapper)

        try:
            async with session_scope() as session:
                await AuditRepository(session).create(
                    actor=actor,
                    actor_type="user",
                    action=f"{method} {path}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details={"status_code": status_code},
                    request_id=request_id,
                )
        except Exception:
            logger.warning("audit log write failed", exc_info=True)
