"""P3-4: AuditMiddleware tests (N6, CLAUDE.md §9).

Every non-GET request must write one row to ``audit_logs``.
GET requests must NOT write a row.
Tests run fully offline (fakeredis, temp SQLite).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import session_scope
from app.main import create_app
from app.models.entities import AuditLog
from app.middleware.audit import _extract_actor, _extract_resource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()


async def _audit_count() -> int:
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(AuditLog)) or 0


async def _latest_audit() -> AuditLog | None:
    async with session_scope() as session:
        result = await session.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1)
        )
        return result.first()


# ---------------------------------------------------------------------------
# Core behaviour: GET vs non-GET
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_does_not_write_audit_log(client):
    before = await _audit_count()
    client.get("/health")
    after = await _audit_count()
    assert after == before


@pytest.mark.asyncio
async def test_post_writes_audit_log(client, agent_headers):
    before = await _audit_count()
    client.post(
        "/api/v1/auth/login",
        json={"email": "sam.agent@clouddesk.demo", "password": "demo"},
    )
    after = await _audit_count()
    assert after == before + 1


@pytest.mark.asyncio
async def test_audit_row_has_correct_fields(client, agent_headers):
    client.post(
        "/api/v1/auth/login",
        json={"email": "sam.agent@clouddesk.demo", "password": "demo"},
    )
    row = await _latest_audit()
    assert row is not None
    assert row.action == "POST /api/v1/auth/login"
    assert row.resource_type == "auth"
    assert row.actor_type == "user"
    assert row.details.get("status_code") == 200


@pytest.mark.asyncio
async def test_authenticated_post_records_actor(client, agent_headers):
    # Use a route that accepts a Bearer token; login itself does not need one.
    # We need any authenticated POST. Let's make a login to get a token then
    # call /api/v1/auth/me via GET — but that's a GET.
    # Instead, verify actor via the login route: actor is anonymous (no Bearer).
    client.post(
        "/api/v1/auth/login",
        json={"email": "sam.agent@clouddesk.demo", "password": "demo"},
    )
    row = await _latest_audit()
    # Login route has no Bearer token, so actor should be anonymous
    assert row is not None
    assert row.actor == "anonymous"


@pytest.mark.asyncio
async def test_bearer_token_sets_actor(client, agent_headers):
    """A non-GET with a valid Bearer token records the caller's email as actor."""
    # We need a non-GET authenticated route. Add one to the app for testing.
    from app.main import create_app as _create_app
    from fastapi import Depends
    from app.core.security import CurrentUser, require_role
    from app.schemas.common import Role

    get_settings.cache_clear()
    app = _create_app()

    @app.post("/test/authenticated")
    async def _authed(user: CurrentUser = Depends(require_role(Role.AGENT))):
        return {"ok": True}

    before = await _audit_count()
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post("/test/authenticated", headers=agent_headers)
    after = await _audit_count()
    assert after == before + 1

    row = await _latest_audit()
    assert row is not None
    assert row.actor == "sam.agent@clouddesk.demo"
    assert row.action == "POST /test/authenticated"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_request_id_recorded_in_audit(client):
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clouddesk.demo", "password": "demo"},
        headers={"X-Request-ID": "test-rid-audit"},
    )
    row = await _latest_audit()
    assert row is not None
    assert row.request_id == "test-rid-audit"


@pytest.mark.asyncio
async def test_resource_type_and_id_extracted(client, agent_headers):
    """Confirm resource_type/resource_id are parsed from the path."""
    # We test the helper directly since we can't easily hit a real ticket route yet
    assert _extract_resource("/api/v1/tickets/CD-1002/run") == ("tickets", "CD-1002")
    assert _extract_resource("/api/v1/auth/login") == ("auth", "login")
    assert _extract_resource("/api/v1/tickets") == ("tickets", "")
    assert _extract_resource("/health") == ("", "")


# ---------------------------------------------------------------------------
# Middleware order verification
# ---------------------------------------------------------------------------

def test_middleware_order_audit_innermost(client):
    """AuditMiddleware is innermost, so request_id from RequestIdMiddleware is
    already present in scope when AuditMiddleware writes the log."""
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clouddesk.demo", "password": "demo"},
        headers={"X-Request-ID": "order-check"},
    )


@pytest.mark.asyncio
async def test_middleware_order_audit_innermost_verified():
    """The request_id set by RequestIdMiddleware appears in the audit row."""
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as c:
        c.post(
            "/api/v1/auth/login",
            json={"email": "admin@clouddesk.demo", "password": "demo"},
            headers={"X-Request-ID": "order-verify-123"},
        )
    get_settings.cache_clear()
    row = await _latest_audit()
    assert row is not None
    assert row.request_id == "order-verify-123"


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

def test_extract_actor_anonymous_when_no_header():
    assert _extract_actor([]) == "anonymous"


def test_extract_actor_anonymous_on_bad_token():
    assert _extract_actor([(b"authorization", b"Bearer bad.token")]) == "anonymous"


def test_extract_resource_various_paths():
    assert _extract_resource("/api/v1/tickets") == ("tickets", "")
    assert _extract_resource("/api/v1/tickets/CD-1001") == ("tickets", "CD-1001")
    assert _extract_resource("/api/v1/approvals/abc-123/approve") == ("approvals", "abc-123")
    assert _extract_resource("/health/ready") == ("", "")
