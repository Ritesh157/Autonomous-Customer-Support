"""Offline pytest harness (CLAUDE.md section 13).

Env vars are forced *before* any ``app`` import so tests never need an API key, Docker, a real
Redis/Qdrant, or touch ``data/``. Auth fixtures (agent/admin/viewer headers) arrive with Phase 3.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="clouddesk-tests-"))

_OFFLINE_ENV = {
    "DEMO_MODE": "true",
    "ENVIRONMENT": "test",
    "LLM_PROVIDER": "fake",
    "LLM_API_KEY": "",
    "EMBEDDING_PROVIDER": "fake",
    "VECTOR_STORE": "memory",
    "QDRANT_URL": "",
    "USE_FAKE_REDIS": "true",
    "REDIS_URL": "",
    "DATABASE_URL": f"sqlite+aiosqlite:///{(_TMP / 'support.db').as_posix()}",
    "CHECKPOINT_DB_PATH": ":memory:",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_API_KEY": "",
    "SUPABASE_JWT_SECRET": "",
    "JWT_SECRET": "test-only-secret",
}
os.environ.update(_OFFLINE_ENV)

import pytest  # noqa: E402
from app.core.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_settings():
    """Settings are lru_cached; clear around every test so monkeypatched env is honoured."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings():
    return get_settings()
