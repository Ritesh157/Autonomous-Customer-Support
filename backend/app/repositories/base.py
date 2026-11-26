"""Shared CRUD and query helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Base


def like_pattern(term: str) -> str:
    """Substring pattern with ``%`` and ``_`` taken literally (use with ``escape="\\"``)."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: str) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create(self, **values: Any) -> ModelT:
        return await self.add(self.model(**values))

    async def update(self, entity: ModelT, **values: Any) -> ModelT:
        for name, value in values.items():
            if name not in self.model.__table__.columns:
                raise ValueError(f"{self.model.__name__} has no column {name!r}")
            setattr(entity, name, value)
        await self.session.flush()
        return entity

    async def count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(self.model)) or 0

    async def _all(self, stmt: Select[Any]) -> list[Any]:
        return list((await self.session.scalars(stmt)).all())

    async def _first(self, stmt: Select[Any]) -> Any | None:
        return (await self.session.scalars(stmt.limit(1))).first()

    async def _paginate(
        self, stmt: Select[Any], page: int, page_size: int
    ) -> tuple[Sequence[Any], int]:
        """Return ``(items, total)``. ``stmt`` must already be ordered."""
        page, page_size = max(page, 1), min(max(page_size, 1), 100)
        total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = await self.session.scalar(total_stmt) or 0
        items = await self._all(stmt.offset((page - 1) * page_size).limit(page_size))
        return items, total
