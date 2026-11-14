import json
import logging

from app.core.config import Settings, get_settings, redact_url
from app.core.logging import log_context, setup_logging


def test_reads_demo_mode_and_llm_provider_from_env(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "OpenAI")
    s = Settings(_env_file=None)
    assert s.demo_mode is False
    assert s.llm_provider == "openai"


def test_defaults_are_offline(monkeypatch):
    for k in ("DEMO_MODE", "LLM_PROVIDER", "VECTOR_STORE", "QDRANT_COLLECTION"):
        monkeypatch.delenv(k, raising=False)
    s = Settings(_env_file=None)
    assert (s.demo_mode, s.llm_provider, s.vector_store) == (True, "fake", "memory")
    assert s.qdrant_collection == "clouddesk_knowledge"
    assert s.max_refund_without_approval == 0
    assert s.approval_required_for_refunds is True


def test_get_settings_is_cached():
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    get_settings.cache_clear()


def test_supabase_secret_wins(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "local")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "supa")
    assert Settings(_env_file=None).effective_jwt_secret == "supa"


def test_model_dump_redacts_secrets(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-real")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:hunter2@db/x")
    s = Settings(_env_file=None)
    dumped = json.dumps(s.model_dump())
    assert "sk-real" not in dumped and "hunter2" not in dumped
    assert s.llm_api_key.get_secret_value() == "sk-real"
    assert "hunter2" in s.database_url  # attributes stay usable for connections


def test_redact_url():
    assert redact_url("redis://u:pw@h/0") == "redis://u:***@h/0"
    assert redact_url("redis://redis:6379/0") == "redis://redis:6379/0"


def test_cors_origin_list(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com")
    assert Settings(_env_file=None).cors_origin_list == ["http://a.com", "http://b.com"]


def test_json_logs_carry_ids(capsys):
    setup_logging()
    log = logging.getLogger("t")
    log.info("plain")
    with log_context(request_id="r1", workflow_id="w1"):
        log.info("bound", extra={"ticket": "CD-1002"})
    log.info("after")
    lines = [json.loads(x) for x in capsys.readouterr().out.strip().splitlines()]
    assert lines[0]["request_id"] is None and lines[0]["workflow_id"] is None
    assert lines[1]["request_id"] == "r1" and lines[1]["workflow_id"] == "w1"
    assert lines[1]["ticket"] == "CD-1002" and lines[1]["message"] == "bound"
    assert lines[2]["request_id"] is None


def test_setup_logging_idempotent_and_exceptions(capsys):
    setup_logging()
    setup_logging()
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("t").exception("failed")
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    assert "ValueError" in json.loads(out[0])["exception"]
