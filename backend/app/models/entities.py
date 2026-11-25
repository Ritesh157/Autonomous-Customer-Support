"""SQLAlchemy 2 models, portable across SQLite (demo) and Postgres (CLAUDE.md section 6).

JSON (not JSONB) and ``String(36)`` UUIDs keep one codebase for both databases. Enum-like
columns are plain strings validated by ``app.schemas.common``. 16 tables.
"""

from __future__ import annotations

import uuid                             # Universally Unique Identifier. Generate unique IDs.
from datetime import UTC, datetime      # datetime: Used to work with dates and times. UTC: Represents Coordinated Universal Time (UTC).
from typing import Any                  # Allow any data type in type hints

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# DeclarativeBase: It provides the foundation for creating database models. it tells SQLAlchemy that Classes that inherit from me will represent database tables.
# Mapped: expected Python data type of a database column.
# mapped_column: used to actually define a database column and its properties.
# relationship: creates the Python-level connection

# A function to generate unique IDs.
def new_id() -> str:
    return str(uuid.uuid4())

# A function to get the current UTC date and time.
def utcnow() -> datetime:
    return datetime.now(UTC)

# A base class for creating database tables using SQLAlchemy
class Base(DeclarativeBase):
    pass

# The main purpose of TimestampMixin is to automatically provide three common database columns to other tables:
# 1. id – Unique ID for every record.
# 2. created_at – When the record was created.
# 3. updated_at – When the record was last updated

class TimestampMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

# Create a Foreign Key column without writing the same code repeatedly
# _fk(): Helper function to create Foreign Key columns
# target: Table and column to reference. Ex: _fk("users.id")
# * : Forces keyword arguments after it. Ex: _fk("users.id", nullable=False)
# nullable: bool = False -> By default, Does not allow NULL values
# ForeignKey(): Connects database tables
# index: Creates an index for faster searching

def _fk(target: str, *, nullable: bool = False) -> Mapped[Any]:
    return mapped_column(String(36), ForeignKey(target), nullable=nullable, index=True)

# The table will store information about users, such as their email address, full name, and role.
class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default="viewer")

# Creating a Customer database table using SQLAlchemy.
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

# Creating a Subscription database table to store subscription information for each customer.

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

# Creating a Workspace database table. It store information about the workspaces created by customers

class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"
    customer_id: Mapped[str] = _fk("customers.id")                  
    name: Mapped[str] = mapped_column(String(255))              # Name of the Workspace. Ex: "Marketing Team", "Sales Department", "HR Department"
    members: Mapped[int] = mapped_column(Integer, default=0)    # number of members in a particular workspace
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

    customer: Mapped[Customer] = relationship()     # creates a Python-level relationship between Ticket and Customer
    messages: Mapped[list[TicketMessage]] = relationship(back_populates="ticket") # A ticket can have multiple messages


# whenever a customer or support agent sends a message related to a support ticket, that message can be stored in this table.

class TicketMessage(TimestampMixin, Base):
    __tablename__ = "ticket_messages"
    ticket_id: Mapped[str] = _fk("tickets.id")
    role: Mapped[str] = mapped_column(String(20))   # stores the role of the person or system that sent the message. (customer, agent, system)
    author_name: Mapped[str] = mapped_column(String(255), default="")   # stores the name of the person who sent the message.
    body: Mapped[str] = mapped_column(Text)             # stores the actual message content
    internal: Mapped[bool] = mapped_column(Boolean, default=False)  # This tells us whether a message is an internal note or a normal customer-visible message.
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)   # This stores attachments associated with a message.

    ticket: Mapped[Ticket] = relationship(back_populates="messages")    # connects TicketMessage back to the Ticket model


# this table stores help articles or knowledge-base articles that customers and support agents can use to find solutions to common problems.
class SupportArticle(TimestampMixin, Base):
    __tablename__ = "support_articles"
    slug: Mapped[str] = mapped_column(String(200), unique=True) # A slug is a URL-friendly version of an article's title. Ex: how-to-reset-password. It can be used to create a readable URL: https://example.com/support/how-to-reset-password
    title: Mapped[str] = mapped_column(String(500)) # Stores the actual title of the support article. Ex: How to Reset Your Password
    category: Mapped[str] = mapped_column(String(40), index=True) # Stores the category to which the article belongs. Ex: Account, Billing, Technical, Payments, Security
    tags: Mapped[list[str]] = mapped_column(JSON, default=list) # This stores multiple tags for an article. Ex: ["password", "login", "account", "security"]
    summary: Mapped[str] = mapped_column(Text, default="") # Stores a short description or overview of the article. Ex: Learn how to reset your account password using your registered email address.
    content: Mapped[str] = mapped_column(Text, default="") # # Stores the complete content of the support article.

# this table stores information about service outages, technical problems, and system disruptions.
# Ex: Website is not loading, Database server is down, Customers are unable to log in, API response time is very slow
class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"
    title: Mapped[str] = mapped_column(String(500)) # Stores the title or name of the incident. Ex: Payment Gateway Not Working, Website Down etc.
    service: Mapped[str] = mapped_column(String(100), index=True)   # Stores the name of the service affected by the incident. Ex: Payment Service, Authentication Service, Email Service
    status: Mapped[str] = mapped_column(String(30), default="investigating")    # Stores the current status of the incident. Ex; identified, monitoring, resolved
    impact: Mapped[str] = mapped_column(Text, default="")   # Stores details about how the incident affects customers or the system.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True) # Stores the date and time when the incident started.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)    # Stores the date and time when the incident was resolved

# This table stores information about a workflow that is executed for a particular support ticket.
class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"
    ticket_id: Mapped[str] = _fk("tickets.id")  # connects a workflow execution to a particular support ticket
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)  # stores the current status of the workflow execution
    current_node: Mapped[str | None] = mapped_column(String(100), nullable=True)    # It stores the name of the current step or node being executed in the workflow.
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # WorkflowState. Stores the workflow's current data and execution context in JSON format
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)   # stores when the workflow started.
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)    # Stores when the workflow execution finished.

# This table stores a history of everything that happens while a workflow is executing.
class WorkflowEvent(TimestampMixin, Base):
    __tablename__ = "workflow_events"
    workflow_id: Mapped[str] = _fk("workflow_runs.id")
    ticket_id: Mapped[str] = _fk("tickets.id")
    event_type: Mapped[str] = mapped_column(String(30)) # Stores the type of event that occurred during workflow execution. Ex: started, node_started, node_complete, tool_called, tool_completed
    node: Mapped[str | None] = mapped_column(String(100), nullable=True)    # stores the name of the workflow node associated with the event. Ex: receive_ticket, analyze_ticket etc.
    tool: Mapped[str | None] = mapped_column(String(100), nullable=True)    # stores the name of the tool used during workflow execution. Ex: search_knowledge_base, send_email, update_ticket
    message: Mapped[str] = mapped_column(Text, default="")  # Stores a human-readable description of what happened during the event.
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True) # stores how long an operation took to execute.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict) # stores additional event information in JSON format.

# This table stores the actions your application plans to perform or performs to resolve a customer's support ticket.
class ResolutionAction(TimestampMixin, Base):
    __tablename__ = "resolution_actions"
    ticket_id: Mapped[str] = _fk("tickets.id")
    workflow_id: Mapped[str | None] = _fk("workflow_runs.id", nullable=True)
    tool: Mapped[str] = mapped_column(String(100))  # stores the name of the tool that should perform the resolution action. Ex: reset_password, send_email, update_ticket
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)   # stores the input arguments that need to be passed to the tool
    status: Mapped[str] = mapped_column(String(30), default="planned")      # stores the current status of the resolution action. Ex: planned, pending_approval, approved
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Stores the output returned by the tool after execution.
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False) # This tells your application whether the action needs approval before execution.
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)    # stores the date and time when the action was executed.

# need human review before an AI agent or workflow performs a potentially risky action.
# Ex: reseting a customer's password, delete an account, issue a refund
class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "approval_requests"
    ticket_id: Mapped[str] = _fk("tickets.id")
    workflow_id: Mapped[str] = _fk("workflow_runs.id")
    action: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # PlannedAction. Stores the action that the AI wants to perform
    risk_level: Mapped[str] = mapped_column(String(20), default="high") # Stores the risk level of the requested action. Low, Medium, High, Critical
    reason: Mapped[str] = mapped_column(Text, default="")               # Stores why the AI is requesting approval
    requested_by: Mapped[str] = mapped_column(String(20), default="ai") # Stores who initiated the approval request. (agent, AI, system)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # Stores the current approval status.
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)      # Stores the name or ID of the person who approved or rejected the request
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)          # Stores the explanation provided by the person who made the decision.
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True) # Stores the date and time when the approval request was approved or rejected.

# tickets that need to be moved to a higher level of support or assigned to a specialized team.
class Escalation(TimestampMixin, Base):
    __tablename__ = "escalations"
    ticket_id: Mapped[str] = _fk("tickets.id")
    reason: Mapped[str] = mapped_column(Text)   # Stores the reason why the ticket is being escalated
    priority: Mapped[str] = mapped_column(String(20), default="high")   # Stores the priority level of the escalation
    status: Mapped[str] = mapped_column(String(20), default="open", index=True) # Stores the current status of the escalation. (open, in-progress, resolved, closed)
    created_by: Mapped[str] = mapped_column(String(20), default="ai")   # Stores who created the escalation (AI, agent, system)
    assigned_team: Mapped[str] = mapped_column(String(100), default="") # Stores the team responsible for handling the escalated ticket
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)    # Stores the date and time when the escalation was resolved.

# stores important information learned about a customer from previous interactions or support tickets.
class CustomerMemory(TimestampMixin, Base):
    __tablename__ = "customer_memory"
    customer_id: Mapped[str] = _fk("customers.id")
    memory_type: Mapped[str] = mapped_column(String(20))    # Stores the category or type of information remembered about the customer.
    content: Mapped[str] = mapped_column(Text)  # Stores the actual information that the AI should remember about the customer
    source_ticket_id: Mapped[str | None] = _fk("tickets.id", nullable=True) # Stores the ID of the ticket from which the memory was created.

# stores a record of important activities and actions performed within your application.
class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    actor: Mapped[str] = mapped_column(String(255)) # Stores the identity of the person or system that performed the action.
    actor_type: Mapped[str] = mapped_column(String(20), default="user") # Stores the type of actor who performed the action (user, AI, system, admin)
    action: Mapped[str] = mapped_column(String(100))    # Stores the name of the action that was performed.
    resource_type: Mapped[str] = mapped_column(String(50), default="")  # Stores the type of resource on which the action was performed (ticket, customer, subscription)
    resource_id: Mapped[str] = mapped_column(String(100), default="")   # Stores the ID of the specific resource affected by the action.
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict) # Stores additional information about the action in JSON format.
    request_id: Mapped[str] = mapped_column(String(128), default="")    # Stores an identifier associated with the incoming application request.
