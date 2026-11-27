"""P2-4: sample data and demo bootstrap (supports F1, F4)."""

import pytest
from app.core.config import get_settings
from app.core.database import create_tables, dispose_engine, session_scope
from app.main import create_app
from app.repositories.customers import CustomerMemoryRepository, CustomerRepository
from app.repositories.knowledge import ArticleRepository, IncidentRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.schemas.common import CATEGORIES
from app.services.seed_service import (
    bootstrap_demo_data,
    data_dir,
    load_articles,
    load_json,
    seed_id,
)
from fastapi.testclient import TestClient

TICKETS = [f"CD-{n}" for n in range(1001, 1014)]


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 's.db').as_posix()}")
    get_settings.cache_clear()


@pytest.fixture
async def db(temp_db):
    await create_tables()
    yield
    await dispose_engine()


async def _counts():
    async with session_scope() as s:
        return (
            await CustomerRepository(s).count(),
            await TicketRepository(s).count(),
            await TicketMessageRepository(s).count(),
            await ArticleRepository(s).count(),
        )


def test_startup_seeds_empty_database_once(temp_db):
    for _ in range(2):  # second startup must not duplicate rows
        with TestClient(create_app()) as client:
            assert client.portal.call(_counts) == (8, 13, 13, 15)


async def test_cd_1002_and_customer_are_readable(db):
    assert (await bootstrap_demo_data())["tickets"] == 13
    async with session_scope() as s:
        ticket = await TicketRepository(s).get_by_number("CD-1002")
        detail = await TicketRepository(s).get_detail(ticket.id)
        assert detail.status == "new" and detail.category is None
        assert len(detail.messages) == 1
        customer = await CustomerRepository(s).get_detail(detail.customer.id)
        assert customer.subscription.seats == 8
        assert customer.workspaces[0].members == 5
        assert await CustomerMemoryRepository(s).for_customer(customer.id)
        assert await IncidentRepository(s).active("authentication")


async def test_second_bootstrap_is_skipped(db):
    await bootstrap_demo_data()
    assert await bootstrap_demo_data() is None
    assert await _counts() == (8, 13, 13, 15)


async def test_nothing_seeded_when_demo_mode_off(db, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    assert await bootstrap_demo_data() is None
    assert await _counts() == (0, 0, 0, 0)


async def test_failed_load_leaves_database_empty(db, monkeypatch):
    def broken():
        raise ValueError("bad article")

    monkeypatch.setattr("app.services.seed_service.load_articles", broken)
    with pytest.raises(ValueError):
        await bootstrap_demo_data()
    assert await _counts() == (0, 0, 0, 0)


def test_sample_data_shape():
    customers = load_json("customers.json")
    assert len(customers) == 8
    assert {c["plan_name"] for c in customers} == {"free", "pro", "business", "enterprise"}
    assert [t["ticket_number"] for t in load_json("tickets.json")] == TICKETS
    keys = {c["key"] for c in customers}
    for name in ("tickets.json", "subscriptions.json", "workspaces.json"):
        assert {row["customer"] for row in load_json(name)} <= keys
    assert {r["category"] for r in load_json("previous_resolutions.json")} <= set(CATEGORIES)
    articles = load_articles()
    assert len(articles) == 15
    assert all(a["content"] and a["summary"] for a in articles)


def test_seed_sql_matches_sample_data():
    sql = (data_dir().parent / "database" / "seed.sql").read_text(encoding="utf-8")
    for number in TICKETS:
        assert f"'{seed_id('ticket', number)}', " in sql or seed_id("ticket", number) in sql
    for c in load_json("customers.json"):
        assert seed_id("customer", c["key"]) in sql
    for a in load_articles():
        assert seed_id("article", a["slug"]) in sql
    assert sql.count("INSERT INTO tickets ") == 13
    assert sql.count("INSERT INTO customers ") == 8
