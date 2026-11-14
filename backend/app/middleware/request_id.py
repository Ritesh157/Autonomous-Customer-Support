"""N3: every response carries ``X-Request-ID``; the id is bound into JSON logs."""

from __future__ import annotations

import logging
import re
import uuid

from app.core.logging import log_context
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "X-Request-ID"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
logger = logging.getLogger(__name__)


def resolve_request_id(incoming: str | None) -> str:
    """Echo a safe client id, otherwise assign a UUID (blocks log/header injection)."""
    if incoming and _SAFE_ID.fullmatch(incoming):
        return incoming
    return str(uuid.uuid4())


class RequestIdMiddleware:
    """Pure ASGI so the id is bound for the whole request, including error responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        request_id = resolve_request_id(incoming)
        scope.setdefault("state", {})["request_id"] = request_id

        started = False

        async def send_with_id(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                headers.append((HEADER.lower().encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        with log_context(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_id)
            except Exception:
                logger.exception("unhandled error")
                if started:
                    raise
                response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
                await response(scope, receive, send_with_id)
