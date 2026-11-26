"""Workflow runs, trace events, resolution actions and approval requests."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update

from app.models.entities import (
    ApprovalRequest,
    ResolutionAction,
    WorkflowEvent,
    WorkflowRun,
    utcnow,
)
from app.repositories.base import BaseRepository


class WorkflowRunRepository(BaseRepository[WorkflowRun]):
    model = WorkflowRun

    async def latest_for_ticket(self, ticket_id: str) -> WorkflowRun | None:
        return await self._first(
            select(WorkflowRun)
            .where(WorkflowRun.ticket_id == ticket_id)
            .order_by(WorkflowRun.started_at.desc())
        )

    async def save_state(
        self,
        run: WorkflowRun,
        state: dict[str, Any],
        status: str | None = None,
        current_node: str | None = None,
    ) -> WorkflowRun:
        # Assign a new dict: in-place JSON mutation is not detected by SQLAlchemy.
        run.state = dict(state)
        if status is not None:
            run.status = status
        if current_node is not None:
            run.current_node = current_node
        await self.session.flush()
        return run


class WorkflowEventRepository(BaseRepository[WorkflowEvent]):
    model = WorkflowEvent

    async def for_workflow(self, workflow_id: str) -> list[WorkflowEvent]:
        return await self._all(
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_id == workflow_id)
            .order_by(WorkflowEvent.created_at)
        )

    async def for_ticket(self, ticket_id: str) -> list[WorkflowEvent]:
        return await self._all(
            select(WorkflowEvent)
            .where(WorkflowEvent.ticket_id == ticket_id)
            .order_by(WorkflowEvent.created_at)
        )

    async def recent(self, limit: int = 20) -> list[WorkflowEvent]:
        return await self._all(
            select(WorkflowEvent).order_by(WorkflowEvent.created_at.desc()).limit(limit)
        )


class ResolutionActionRepository(BaseRepository[ResolutionAction]):
    model = ResolutionAction

    async def for_ticket(self, ticket_id: str) -> list[ResolutionAction]:
        return await self._all(
            select(ResolutionAction)
            .where(ResolutionAction.ticket_id == ticket_id)
            .order_by(ResolutionAction.created_at)
        )


class ApprovalRepository(BaseRepository[ApprovalRequest]):
    model = ApprovalRequest

    async def list_by_status(self, status: str | None = None) -> list[ApprovalRequest]:
        stmt = select(ApprovalRequest)
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        return await self._all(stmt.order_by(ApprovalRequest.created_at.desc()))

    async def pending_for_workflow(self, workflow_id: str) -> ApprovalRequest | None:
        return await self._first(
            select(ApprovalRequest).where(
                ApprovalRequest.workflow_id == workflow_id,
                ApprovalRequest.status == "pending",
            )
        )

    async def decide(
        self, approval_id: str, status: str, decided_by: str, note: str | None = None
    ) -> ApprovalRequest | None:
        """Record a decision once. Returns ``None`` if missing or no longer pending.

        The conditional UPDATE means two concurrent decisions cannot both succeed.
        """
        if status not in {"approved", "rejected"}:
            raise ValueError(f"invalid approval decision {status!r}")
        result = await self.session.execute(
            update(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id, ApprovalRequest.status == "pending")
            .values(
                status=status, decided_by=decided_by, decision_note=note, decided_at=utcnow()
            )
        )
        if result.rowcount != 1:
            return None
        return await self.session.get(ApprovalRequest, approval_id, populate_existing=True)
