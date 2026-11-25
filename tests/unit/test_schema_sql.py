"""P2-2: database/schema.sql, RLS and migrations agree with the SQLAlchemy models."""

import re
from pathlib import Path

from app.models.entities import Base

DB = Path(__file__).resolve().parents[2] / "database"
SCHEMA = (DB / "schema.sql").read_text(encoding="utf-8")
RLS = (DB / "rls_policies.sql").read_text(encoding="utf-8")


def _sql_tables() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\);", SCHEMA, re.DOTALL):
        cols = set()
        for line in m.group(2).splitlines():
            first = line.strip().split(" ", 1)[0]
            if first and first not in {"PRIMARY", "FOREIGN", "UNIQUE", "CONSTRAINT"}:
                cols.add(first)
        found[m.group(1)] = cols
    return found


def test_tables_and_columns_match_models():
    sql = _sql_tables()
    models = {t.name: {c.name for c in t.columns} for t in Base.metadata.tables.values()}
    assert len(sql) == 16
    assert sql == models


def test_no_sqlite_only_or_jsonb_types():
    assert "JSONB" not in SCHEMA
    assert "TIMESTAMP WITH TIME ZONE" in SCHEMA


def test_updated_at_trigger_on_every_table():
    assert "set_updated_at()" in SCHEMA
    for name in _sql_tables():
        assert f"CREATE TRIGGER trg_{name}_updated_at" in SCHEMA


def test_rls_enabled_on_every_table_with_no_write_policies():
    for name in _sql_tables():
        assert f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY;" in RLS
    assert not re.search(r"FOR (INSERT|UPDATE|DELETE|ALL)", RLS)
    assert "service" in RLS.lower()


def test_migrations_are_numbered_and_additive():
    files = sorted(p.name for p in (DB / "migrations").glob("*.sql"))
    assert files == ["0001_initial_schema.sql", "0002_enable_rls.sql"]
    for p in (DB / "migrations").glob("*.sql"):
        assert not re.search(r"\bDROP\s+(TABLE|COLUMN)\b", p.read_text(encoding="utf-8"), re.IGNORECASE)
