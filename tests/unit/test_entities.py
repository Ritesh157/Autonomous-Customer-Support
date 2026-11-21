"""P2-1: category enum and SQLAlchemy entities."""

import pytest
from app.models.entities import Base, Customer, Ticket, TicketMessage
from app.schemas.common import CATEGORIES, Category, Severity, TicketStatus
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

EXPECTED_TABLES = {
    "profiles", "customers", "subscriptions", "workspaces", "products", "tickets",
    "ticket_messages", "support_articles", "incidents", "workflow_runs", "workflow_events",
    "resolution_actions", "approval_requests", "escalations", "customer_memory", "audit_logs",
}


def test_exactly_ten_categories():
    assert set(CATEGORIES) == {
        "login_issue", "billing", "api_failure", "workspace_permissions", "storage_quota",
        "integration", "feature_request", "account", "security", "other",
    }
    assert len(Category) == 10


def test_status_and_severity_values():
    assert [s.value for s in Severity] == ["low", "medium", "high", "critical"]
    assert len(TicketStatus) == 7


def test_sixteen_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_portable_types_only():
    for table in Base.metadata.tables.values():
        for col in table.columns:
            name = type(col.type).__name__.upper()
            assert "JSONB" not in name and "UUID" not in name
    assert Base.metadata.tables["tickets"].c.id.type.length == 36


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_ticket_roundtrip(session):
    c = Customer(name="Ada", email="ada@example.com", plan_name="pro")
    session.add(c)
    session.flush()
    t = Ticket(ticket_number="CD-9999", customer_id=c.id, subject="s", body="b", tags=["x"])
    t.messages.append(TicketMessage(role="customer", body="hi"))
    session.add(t)
    session.commit()
    got = session.scalars(select(Ticket)).one()
    assert got.status == "new" and got.tags == ["x"] and len(got.id) == 36
    assert got.messages[0].internal is False and got.created_at is not None
