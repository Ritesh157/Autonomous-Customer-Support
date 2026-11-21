"""P1-3: the harness forces an offline configuration before the app is imported."""

import os
from pathlib import Path

from app.core.config import get_settings


def test_offline_defaults(settings):
    assert settings.demo_mode is True
    assert settings.llm_provider == "fake"
    assert settings.vector_store == "memory"
    assert settings.use_fake_redis is True
    assert settings.checkpoint_db_path == ":memory:"
    assert settings.llm_api_key.get_secret_value() == ""


def test_database_is_temp_not_repo_data(settings):
    assert "data/support.db" not in settings.database_url
    assert Path(settings.database_url.rsplit("///", 1)[-1]).parent != Path("data").resolve()


def test_settings_cache_cleared_between_tests(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "OpenAI")
    assert get_settings().llm_provider == "openai"


def test_previous_override_did_not_leak():
    assert os.environ["LLM_PROVIDER"] == "fake"
    assert get_settings().llm_provider == "fake"
