"""Tickets, ticket messages and escalations."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.entities import Escalation, Ticket, TicketMessage
from app.repositories.base import BaseRepository, like_pattern

_NUMBER_PREFIX = "CD-"
_FIRST_NUMBER = 1001


class TicketRepository(BaseRepository[Ticket]):
    model = Ticket

    async def get_detail(self, ticket_id: str) -> Ticket | None:
        """Ticket with customer and messages loaded."""
        return await self._first(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.customer), selectinload(Ticket.messages))
        )

    async def get_by_number(self, ticket_number: str) -> Ticket | None:
        return await self._first(select(Ticket).where(Ticket.ticket_number == ticket_number))

    async def search(
        self,
        status: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Ticket], int]:
        stmt = select(Ticket).options(selectinload(Ticket.customer))
        if status:
            stmt = stmt.where(Ticket.status == status)
        if severity:
            stmt = stmt.where(Ticket.severity == severity)
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    Ticket.subject.ilike(pattern, escape="\\"),
                    Ticket.ticket_number.ilike(pattern, escape="\\"),
                )
            )
        stmt = stmt.order_by(Ticket.created_at.desc(), Ticket.ticket_number.desc())
        return await self._paginate(stmt, page, page_size)

    async def history_for_customer(
        self, customer_id: str, exclude_ticket_id: str | None = None, limit: int = 10
    ) -> list[Ticket]:
        stmt = select(Ticket).where(Ticket.customer_id == customer_id)
        if exclude_ticket_id:
            stmt = stmt.where(Ticket.id != exclude_ticket_id)
        return await self._all(
            stmt.options(selectinload(Ticket.customer))
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )

    async def next_ticket_number(self) -> str:
        """``CD-<n+1>``. The unique constraint rejects a concurrent duplicate."""
        numbers = await self._all(
            select(Ticket.ticket_number).where(Ticket.ticket_number.like(f"{_NUMBER_PREFIX}%"))
        )
        used = [int(n[3:]) for n in numbers if n[3:].isdigit()]
        return f"{_NUMBER_PREFIX}{max(used, default=_FIRST_NUMBER - 1) + 1}"

    async def counts_by(self, column: str) -> dict[str, int]:
        """Ticket counts grouped by ``status``, ``severity`` or ``category`` (nulls skipped)."""
        if column not in {"status", "severity", "category"}:
            raise ValueError(f"cannot group tickets by {column!r}")
        col = getattr(Ticket, column)
        rows = await self.session.execute(
            select(col, func.count()).where(col.is_not(None)).group_by(col)
        )
        return {key: total for key, total in rows.all()}


class TicketMessageRepository(BaseRepository[TicketMessage]):
    model = TicketMessage

    async def for_ticket(
        self, ticket_id: str, include_internal: bool = True
    ) -> list[TicketMessage]:
        """Oldest first."""
        stmt = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id)
        if not include_internal:
            stmt = stmt.where(TicketMessage.internal.is_(False))
        return await self._all(stmt.order_by(TicketMessage.created_at))


class EscalationRepository(BaseRepository[Escalation]):
    model = Escalation

    async def list_by_status(self, status: str | None = None) -> list[Escalation]:
        stmt = select(Escalation)
        if status:
            stmt = stmt.where(Escalation.status == status)
        return await self._all(stmt.order_by(Escalation.created_at.desc()))

    async def latest_for_ticket(self, ticket_id: str) -> Escalation | None:
        return await self._first(
            select(Escalation)
            .where(Escalation.ticket_id == ticket_id)
            .order_by(Escalation.created_at.desc())
        )
