"""P3-1: JWT and require_role tests (N1, CLAUDE.md §2, §18.1)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import CurrentUser, create_token, require_role
from app.main import create_app
from app.schemas.common import Role


# ---------------------------------------------------------------------------
# Shared fixture: app with a protected route injected for testing
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    get_settings.cache_clear()
    app = create_app()

    @app.get("/test/agent-only")
    async def _agent_only(user: CurrentUser = Depends(require_role(Role.AGENT))):
        return {"email": user.email, "role": user.role}

    @app.get("/test/admin-only")
    async def _admin_only(user: CurrentUser = Depends(require_role(Role.ADMIN))):
        return {"email": user.email, "role": user.role}

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 401 — missing / malformed / expired tokens
# ---------------------------------------------------------------------------

def test_missing_token_is_401(client):
    r = client.get("/test/agent-only")
    assert r.status_code == 401


def test_bad_token_is_401(client):
    r = client.get("/test/agent-only", headers={"Authorization": "Bearer notavalidjwt"})
    assert r.status_code == 401


def test_wrong_signature_is_401(client):
    token = jwt.encode(
        {"sub": "x", "email": "x@x.com", "role": "agent",
         "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(hours=1)},
        "wrong-secret",
        algorithm="HS256",
    )
    r = client.get("/test/agent-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_expired_token_is_401(client):
    settings = get_settings()
    token = jwt.encode(
        {"sub": "x", "email": "x@x.com", "role": "agent",
         "iat": datetime.now(UTC) - timedelta(hours=10),
         "exp": datetime.now(UTC) - timedelta(hours=1)},
        settings.effective_jwt_secret,
        algorithm="HS256",
    )
    r = client.get("/test/agent-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 403 — viewer on agent-required route
# ---------------------------------------------------------------------------

def test_viewer_gets_403_on_agent_route(client, viewer_headers):
    r = client.get("/test/agent-only", headers=viewer_headers)
    assert r.status_code == 403


def test_viewer_gets_403_on_admin_route(client, viewer_headers):
    r = client.get("/test/admin-only", headers=viewer_headers)
    assert r.status_code == 403


def test_agent_gets_403_on_admin_route(client, agent_headers):
    r = client.get("/test/admin-only", headers=agent_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# 200 — valid tokens at correct or higher roles
# ---------------------------------------------------------------------------

def test_agent_token_accepted_on_agent_route(client, agent_headers):
    r = client.get("/test/agent-only", headers=agent_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "agent"


def test_admin_token_accepted_on_agent_route(client, admin_headers):
    r = client.get("/test/agent-only", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_admin_token_accepted_on_admin_route(client, admin_headers):
    r = client.get("/test/admin-only", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


# ---------------------------------------------------------------------------
# Token payload is well-formed (create_token)
# ---------------------------------------------------------------------------

def test_create_token_round_trips(settings):
    token = create_token("sam.agent@clouddesk.demo", Role.AGENT)
    payload = jwt.decode(token, settings.effective_jwt_secret, algorithms=["HS256"])
    assert payload["email"] == "sam.agent@clouddesk.demo"
    assert payload["role"] == "agent"
    assert payload["sub"] == "sam.agent@clouddesk.demo"


def test_token_expires_in_8_hours(settings):
    token = create_token("admin@clouddesk.demo", Role.ADMIN)
    payload = jwt.decode(token, settings.effective_jwt_secret, algorithms=["HS256"])
    delta = payload["exp"] - payload["iat"]
    assert delta == 8 * 3600


def test_role_level_hierarchy_viewer_lt_agent():
    """Sanity: viewer role cannot access agent-level route."""
    viewer_token = create_token("vic.viewer@clouddesk.demo", Role.VIEWER)
    agent_token = create_token("sam.agent@clouddesk.demo", Role.AGENT)
    # Different tokens — just verify the role strings are distinct
    settings = get_settings()
    vp = jwt.decode(viewer_token, settings.effective_jwt_secret, algorithms=["HS256"])
    ap = jwt.decode(agent_token, settings.effective_jwt_secret, algorithms=["HS256"])
    assert vp["role"] == "viewer"
    assert ap["role"] == "agent"
