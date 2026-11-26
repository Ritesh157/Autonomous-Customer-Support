"""Profiles, customers, subscriptions, workspaces and long-term customer memory."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.entities import (
    Customer,
    CustomerMemory,
    Profile,
    Subscription,
    Workspace,
)
from app.repositories.base import BaseRepository, like_pattern


class ProfileRepository(BaseRepository[Profile]):
    model = Profile

    async def get_by_email(self, email: str) -> Profile | None:
        return await self._first(
            select(Profile).where(func.lower(Profile.email) == email.strip().lower())
        )


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    async def get_detail(self, customer_id: str) -> Customer | None:
        """Customer with subscription and workspaces loaded."""
        return await self._first(
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.subscription), selectinload(Customer.workspaces))
        )

    async def get_by_email(self, email: str) -> Customer | None:
        return await self._first(
            select(Customer).where(func.lower(Customer.email) == email.strip().lower())
        )

    async def search(
        self, search: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[Sequence[Customer], int]:
        stmt = select(Customer)
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(pattern, escape="\\"),
                    Customer.email.ilike(pattern, escape="\\"),
                    Customer.company.ilike(pattern, escape="\\"),
                )
            )
        return await self._paginate(stmt.order_by(Customer.name, Customer.id), page, page_size)


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    async def for_customer(self, customer_id: str) -> Subscription | None:
        return await self._first(
            select(Subscription)
            .where(Subscription.customer_id == customer_id)
            .order_by(Subscription.created_at.desc())
        )


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def for_customer(self, customer_id: str) -> list[Workspace]:
        return await self._all(
            select(Workspace)
            .where(Workspace.customer_id == customer_id)
            .order_by(Workspace.name)
        )


class CustomerMemoryRepository(BaseRepository[CustomerMemory]):
    model = CustomerMemory

    async def for_customer(
        self, customer_id: str, limit: int | None = None
    ) -> list[CustomerMemory]:
        """Newest first."""
        stmt = (
            select(CustomerMemory)
            .where(CustomerMemory.customer_id == customer_id)
            .order_by(CustomerMemory.created_at.desc())
        )
        return await self._all(stmt.limit(limit) if limit is not None else stmt)

    async def add_note(
        self,
        customer_id: str,
        memory_type: str,
        content: str,
        source_ticket_id: str | None = None,
    ) -> CustomerMemory | None:
        """Insert unless this exact note exists (returns ``None``).

        Callers must scrub secrets first; that is the memory layer's job.
        """
        duplicate = await self._first(
            select(CustomerMemory).where(
                CustomerMemory.customer_id == customer_id,
                CustomerMemory.memory_type == memory_type,
                CustomerMemory.content == content,
            )
        )
        if duplicate:
            return None
        return await self.create(
            customer_id=customer_id,
            memory_type=memory_type,
            content=content,
            source_ticket_id=source_ticket_id,
        )
