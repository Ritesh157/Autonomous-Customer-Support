import json
import logging
import uuid

import pytest
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()


@pytest.mark.parametrize("path", ["/health", "/health/live"])
def test_liveness(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_ok_offline(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert set(body["checks"]) == {"database", "redis", "vector_store", "llm"}


def test_ready_degraded_without_leaking_secrets(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE", "qdrant")
    monkeypatch.setenv("QDRANT_URL", "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:hunter2@db/x")
    get_settings.cache_clear()
    # No ``with``: the lifespan would try to connect to this unreachable database.
    r = TestClient(create_app()).get("/health/ready")
    get_settings.cache_clear()
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"
    assert "hunter2" not in r.text and "postgresql" not in r.text


def test_every_response_has_request_id(client):
    for path in ("/health", "/health/ready", "/nope"):
        r = client.get(path)
        uuid.UUID(r.headers["X-Request-ID"])


def test_safe_incoming_id_is_echoed(client):
    r = client.get("/health", headers={"X-Request-ID": "abc-123.x_Y"})
    assert r.headers["X-Request-ID"] == "abc-123.x_Y"


def test_unsafe_incoming_id_is_replaced(client):
    r = client.get("/health", headers={"X-Request-ID": "bad id;<script>"})
    assert r.headers["X-Request-ID"] != "bad id;<script>"
    uuid.UUID(r.headers["X-Request-ID"])


def test_cors_exposes_request_id(client):
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert "x-request-id" in r.headers["access-control-expose-headers"].lower()


def test_500_still_has_request_id_and_logs_it(capsys):
    get_settings.cache_clear()
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("x")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/boom", headers={"X-Request-ID": "rid-500"})
    get_settings.cache_clear()
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal Server Error"}
    assert r.headers["X-Request-ID"] == "rid-500"
    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.startswith("{")]
    assert any(line["request_id"] == "rid-500" and line["level"] == "ERROR" for line in lines)
    logging.getLogger().handlers.clear()
