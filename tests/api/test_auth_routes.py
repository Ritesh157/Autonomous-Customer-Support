"""P3-2: Demo auth routes (POST /api/v1/auth/login, GET /api/v1/auth/me)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login — demo mode
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "email,expected_role",
    [
        ("admin@clouddesk.demo", "admin"),
        ("sam.agent@clouddesk.demo", "agent"),
        ("vic.viewer@clouddesk.demo", "viewer"),
    ],
)
def test_login_all_demo_users(client, email, expected_role):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "demo"})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert body["user"]["email"] == email
    assert body["user"]["role"] == expected_role
    assert body["user"]["full_name"]  # non-empty


def test_login_returns_8h_token(client):
    import jwt as _jwt

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "sam.agent@clouddesk.demo", "password": "demo"},
    )
    assert r.status_code == 200
    settings = get_settings()
    payload = _jwt.decode(
        r.json()["token"], settings.effective_jwt_secret, algorithms=["HS256"]
    )
    assert payload["exp"] - payload["iat"] == 8 * 3600


def test_login_wrong_password_is_401(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "sam.agent@clouddesk.demo", "password": "wrongpassword"},
    )
    assert r.status_code == 401


def test_login_unknown_email_is_401(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@clouddesk.demo", "password": "demo"},
    )
    assert r.status_code == 401


def test_login_no_service_secret_in_response(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@clouddesk.demo", "password": "demo"},
    )
    settings = get_settings()
    secret = settings.effective_jwt_secret
    assert secret not in r.text


def test_login_disabled_outside_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as c:
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "admin@clouddesk.demo", "password": "demo"},
        )
    get_settings.cache_clear()
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------

def test_me_returns_current_user(client, agent_headers):
    r = client.get("/api/v1/auth/me", headers=agent_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "sam.agent@clouddesk.demo"
    assert body["role"] == "agent"
    assert body["full_name"]


def test_me_no_token_is_401(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_bad_token_is_401(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token.here"})
    assert r.status_code == 401


def test_me_works_for_all_roles(client, admin_headers, agent_headers, viewer_headers):
    for headers, expected_role in [
        (admin_headers, "admin"),
        (agent_headers, "agent"),
        (viewer_headers, "viewer"),
    ]:
        r = client.get("/api/v1/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["role"] == expected_role
