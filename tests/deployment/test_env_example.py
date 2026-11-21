"""P1-4: .env.example lists every Settings variable and holds placeholders only."""

import re
from pathlib import Path

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
ENV = (ROOT / ".env.example").read_text(encoding="utf-8")
KEYS = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", ENV, re.M))


def test_every_setting_is_listed():
    missing = {n.upper() for n in Settings.model_fields} - KEYS
    assert not missing, missing


def test_no_real_secrets():
    for key in ("LLM_API_KEY", "QDRANT_API_KEY", "LANGCHAIN_API_KEY", "SUPABASE_JWT_SECRET"):
        assert re.search(rf"^{key}=$", ENV, re.M)


def test_makefile_has_core_targets():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    for t in ("setup", "backend", "test", "lint", "seed", "ingest", "demo", "mcp"):
        assert re.search(rf"^{t}:", mk, re.M), t
