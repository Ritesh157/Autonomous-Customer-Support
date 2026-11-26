"""P2-3: repository layer against a throwaway SQLite database."""

import pytest
from app.core.database import create_tables, dispose_engine, session_scope
from app.repositories.audit import AuditRepository
from app.repositories.customers import CustomerMemoryRepository, CustomerRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.repositories.workflows import ApprovalRepository, WorkflowRunRepository
from sqlalchemy.exc import IntegrityError


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'r.db').as_posix()}")
    from app.core.config import get_settings

    get_settings.cache_clear()
    await create_tables()
    yield
    await dispose_engine()


async def _customer(session, email="ada@example.com", **kw):
    return await CustomerRepository(session).create(name="Ada", email=email, **kw)


async def _ticket(session, customer, number="CD-1001", **kw):
    values = {"subject": "Login fails", "body": "b"} | kw
    return await TicketRepository(session).create(
        ticket_number=number, customer_id=customer.id, **values
    )


async def test_ticket_search_detail_and_counts(db):
    async with session_scope() as s:
        c = await _customer(s)
        repo = TicketRepository(s)
        assert await repo.next_ticket_number() == "CD-1001"
        t = await _ticket(s, c, severity="high")
        await _ticket(s, c, "CD-1002", subject="100% refund", status="resolved")
        await TicketMessageRepository(s).create(ticket_id=t.id, role="customer", body="hi")
        await TicketMessageRepository(s).create(
            ticket_id=t.id, role="agent", body="note", internal=True
        )

    async with session_scope() as s:
        repo = TicketRepository(s)
        items, total = await repo.search(page=1, page_size=1)
        assert total == 2 and len(items) == 1 and items[0].customer.name == "Ada"
        assert (await repo.search(severity="high"))[1] == 1
        assert (await repo.search(search="%"))[1] == 1  # wildcard is literal
        assert (await repo.next_ticket_number()) == "CD-1003"
        assert await repo.counts_by("status") == {"new": 1, "resolved": 1}
        detail = await repo.get_detail(t.id)
        assert len(detail.messages) == 2
        public = await TicketMessageRepository(s).for_ticket(t.id, include_internal=False)
        assert [m.body for m in public] == ["hi"]
        assert len(await repo.history_for_customer(c.id, exclude_ticket_id=t.id)) == 1


async def test_session_scope_rolls_back_on_error(db):
    with pytest.raises(RuntimeError):
        async with session_scope() as s:
            await _customer(s)
            raise RuntimeError("boom")
    async with session_scope() as s:
        assert await CustomerRepository(s).count() == 0


async def test_foreign_keys_enforced(db):
    with pytest.raises(IntegrityError):
        async with session_scope() as s:
            await TicketRepository(s).create(
                ticket_number="CD-1", customer_id="nope", subject="s", body="b"
            )


async def test_memory_notes_are_deduplicated(db):
    async with session_scope() as s:
        c = await _customer(s)
        repo = CustomerMemoryRepository(s)
        assert await repo.add_note(c.id, "note", "prefers email")
        assert await repo.add_note(c.id, "note", "prefers email") is None
        assert len(await repo.for_customer(c.id)) == 1


async def test_workflow_state_persists_and_approval_decided_once(db):
    async with session_scope() as s:
        t = await _ticket(s, await _customer(s))
        runs = WorkflowRunRepository(s)
        run = await runs.create(ticket_id=t.id)
        state = {"completed_nodes": ["understand_ticket"]}
        await runs.save_state(run, state)
        state["completed_nodes"] = ["x", "y"]
        approval = await ApprovalRepository(s).create(ticket_id=t.id, workflow_id=run.id)

    async with session_scope() as s:
        run = await WorkflowRunRepository(s).latest_for_ticket(t.id)
        assert run.state == {"completed_nodes": ["understand_ticket"]}
        approvals = ApprovalRepository(s)
        assert await approvals.pending_for_workflow(run.id)
        done = await approvals.decide(approval.id, "approved", "sam.agent@clouddesk.demo")
        assert done.status == "approved" and done.decided_at is not None
        assert await approvals.decide(approval.id, "rejected", "x") is None
        assert await approvals.pending_for_workflow(run.id) is None
        with pytest.raises(ValueError):
            await approvals.decide(approval.id, "pending", "x")


async def test_update_rejects_unknown_column_and_audit_is_append_only(db):
    async with session_scope() as s:
        c = await _customer(s)
        with pytest.raises(ValueError):
            await CustomerRepository(s).update(c, nope=1)
        audit = AuditRepository(s)
        entry = await audit.create(actor="a", action="POST /x")
        with pytest.raises(NotImplementedError):
            await audit.update(entry, action="changed")
