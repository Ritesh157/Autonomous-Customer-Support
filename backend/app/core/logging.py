"""JSON logging with ``request_id`` and ``workflow_id`` on every line (section 16)."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_workflow_id: ContextVar[str | None] = ContextVar("workflow_id", default=None)

_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


@contextmanager
def log_context(
    request_id: str | None = None, workflow_id: str | None = None
) -> Iterator[None]:
    """Bind ids for the current task; only the ids passed are changed, then restored."""
    tokens = []
    if request_id is not None:
        tokens.append((_request_id, _request_id.set(request_id)))
    if workflow_id is not None:
        tokens.append((_workflow_id, _workflow_id.set(workflow_id)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
            "workflow_id": _workflow_id.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: int | str = logging.INFO) -> None:
    """Install one JSON stream handler on the root logger (idempotent)."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_clouddesk", False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._clouddesk = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)
