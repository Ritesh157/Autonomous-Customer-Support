"""Audit log: append and read only. There is deliberately no update path."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.entities import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def update(self, entity: AuditLog, **values: Any) -> AuditLog:
        raise NotImplementedError("audit logs are append-only")

    async def recent(self, limit: int = 100, resource_type: str | None = None) -> list[AuditLog]:
        stmt = select(AuditLog)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        return await self._all(stmt.order_by(AuditLog.created_at.desc()).limit(limit))
