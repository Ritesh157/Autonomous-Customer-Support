"""SQLAlchemy 2 models, portable across SQLite (demo) and Postgres (CLAUDE.md section 6).

JSON (not JSONB) and ``String(36)`` UUIDs keep one codebase for both databases. Enum-like
columns are plain strings validated by ``app.schemas.common``. 16 tables.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


def _fk(target: str, *, nullable: bool = False) -> Mapped[Any]:
    return mapped_column(String(36), ForeignKey(target), nullable=nullable, index=True)


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default="viewer")


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    company: Mapped[str] = mapped_column(String(255), default="")
    plan_name: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    region: Mapped[str] = mapped_column(String(50), default="")
    lifetime_value: Mapped[float] = mapped_column(Float, default=0.0)

    subscription: Mapped[Subscription | None] = relationship(
        back_populates="customer", uselist=False
    )
    workspaces: Mapped[list[Workspace]] = relationship(back_populates="customer")


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    customer_id: Mapped[str] = _fk("customers.id")
    plan: Mapped[str] = mapped_column(String(20))
    seats: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="active")
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mrr: Mapped[float] = mapped_column(Float, default=0.0)
    storage_quota_gb: Mapped[float] = mapped_column(Float, default=0.0)
    storage_used_gb: Mapped[float] = mapped_column(Float, default=0.0)
    api_rate_limit: Mapped[int] = mapped_column(Integer, default=0)

    customer: Mapped[Customer] = relationship(back_populates="subscription")


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"
    customer_id: Mapped[str] = _fk("customers.id")
    name: Mapped[str] = mapped_column(String(255))
    members: Mapped[int] = mapped_column(Integer, default=0)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    customer: Mapped[Customer] = relationship(back_populates="workspaces")


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[str] = _fk("customers.id")
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(20), default="web")
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    escalation_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[str] = mapped_column(String(20), default="not_required")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer] = relationship()
    messages: Mapped[list[TicketMessage]] = relationship(back_populates="ticket")


class TicketMessage(TimestampMixin, Base):
    __tablename__ = "ticket_messages"
    ticket_id: Mapped[str] = _fk("tickets.id")
    role: Mapped[str] = mapped_column(String(20))
    author_name: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text)
    internal: Mapped[bool] = mapped_column(Boolean, default=False)
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    ticket: Mapped[Ticket] = relationship(back_populates="messages")


class SupportArticle(TimestampMixin, Base):
    __tablename__ = "support_articles"
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(40), index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"
    title: Mapped[str] = mapped_column(String(500))
    service: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(30), default="investigating")
    impact: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"
    ticket_id: Mapped[str] = _fk("tickets.id")
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    current_node: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # WorkflowState
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowEvent(TimestampMixin, Base):
    __tablename__ = "workflow_events"
    workflow_id: Mapped[str] = _fk("workflow_runs.id")
    ticket_id: Mapped[str] = _fk("tickets.id")
    event_type: Mapped[str] = mapped_column(String(30))
    node: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ResolutionAction(TimestampMixin, Base):
    __tablename__ = "resolution_actions"
    ticket_id: Mapped[str] = _fk("tickets.id")
    workflow_id: Mapped[str | None] = _fk("workflow_runs.id", nullable=True)
    tool: Mapped[str] = mapped_column(String(100))
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="planned")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "approval_requests"
    ticket_id: Mapped[str] = _fk("tickets.id")
    workflow_id: Mapped[str] = _fk("workflow_runs.id")
    action: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # PlannedAction
    risk_level: Mapped[str] = mapped_column(String(20), default="high")
    reason: Mapped[str] = mapped_column(Text, default="")
    requested_by: Mapped[str] = mapped_column(String(20), default="ai")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Escalation(TimestampMixin, Base):
    __tablename__ = "escalations"
    ticket_id: Mapped[str] = _fk("tickets.id")
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="high")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_by: Mapped[str] = mapped_column(String(20), default="ai")
    assigned_team: Mapped[str] = mapped_column(String(100), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CustomerMemory(TimestampMixin, Base):
    __tablename__ = "customer_memory"
    customer_id: Mapped[str] = _fk("customers.id")
    memory_type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    source_ticket_id: Mapped[str | None] = _fk("tickets.id", nullable=True)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    actor: Mapped[str] = mapped_column(String(255))
    actor_type: Mapped[str] = mapped_column(String(20), default="user")
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(50), default="")
    resource_id: Mapped[str] = mapped_column(String(100), default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    request_id: Mapped[str] = mapped_column(String(128), default="")
