"""Support articles, incidents and products."""

from __future__ import annotations

from sqlalchemy import func, or_, select

from app.models.entities import Incident, Product, SupportArticle
from app.repositories.base import BaseRepository, like_pattern


class ArticleRepository(BaseRepository[SupportArticle]):
    model = SupportArticle

    async def get_by_slug(self, slug: str) -> SupportArticle | None:
        return await self._first(select(SupportArticle).where(SupportArticle.slug == slug))

    async def search(
        self, search: str | None = None, category: str | None = None
    ) -> list[SupportArticle]:
        stmt = select(SupportArticle)
        if category:
            stmt = stmt.where(SupportArticle.category == category)
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    SupportArticle.title.ilike(pattern, escape="\\"),
                    SupportArticle.summary.ilike(pattern, escape="\\"),
                    SupportArticle.content.ilike(pattern, escape="\\"),
                )
            )
        return await self._all(stmt.order_by(SupportArticle.title))


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    async def active(self, service: str | None = None) -> list[Incident]:
        """Incidents that are not resolved, newest first."""
        stmt = select(Incident).where(Incident.status != "resolved")
        if service:
            stmt = stmt.where(func.lower(Incident.service) == service.strip().lower())
        return await self._all(stmt.order_by(Incident.started_at.desc()))


class ProductRepository(BaseRepository[Product]):
    model = Product

    async def list_all(self) -> list[Product]:
        return await self._all(select(Product).order_by(Product.name))
