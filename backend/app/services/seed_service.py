"""Load ``sample_data/`` into an empty database. Run with ``make seed``.

IDs are derived from natural keys (uuid5), so every environment gets the same demo ids and
``database/seed.sql`` matches the SQLite demo. ``previous_resolutions.json`` is not a table;
the Knowledge Agent reads it later.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import create_tables, dispose_engine, session_scope
from app.core.logging import setup_logging
from app.repositories.customers import (
    CustomerMemoryRepository,
    CustomerRepository,
    ProfileRepository,
    SubscriptionRepository,
    WorkspaceRepository,
)
from app.repositories.knowledge import (
    ArticleRepository,
    IncidentRepository,
    ProductRepository,
)
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.schemas.common import Category

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "clouddesk.demo")

DEMO_PROFILES = (
    ("admin@clouddesk.demo", "Demo Admin", "admin"),
    ("sam.agent@clouddesk.demo", "Sam Agent", "agent"),
    ("vic.viewer@clouddesk.demo", "Vic Viewer", "viewer"),
)


def seed_id(kind: str, key: str) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, f"{kind}:{key}"))


def data_dir() -> Path:
    """``SAMPLE_DATA_DIR``; relative paths are resolved from the repository root."""
    path = Path(get_settings().sample_data_dir)
    return path if path.is_absolute() else _REPO_ROOT / path


def load_json(name: str) -> list[dict[str, Any]]:
    return json.loads((data_dir() / name).read_text(encoding="utf-8"))


def load_articles() -> list[dict[str, Any]]:
    """Knowledge-base markdown with YAML front matter. The file name is the slug."""
    articles = []
    for path in sorted((data_dir() / "knowledge_base").glob("*.md")):
        parts = path.read_text(encoding="utf-8").split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f"{path.name}: missing front matter")
        meta = yaml.safe_load(parts[1])
        articles.append(
            {
                "slug": path.stem,
                "title": meta["title"],
                "category": Category(meta["category"]).value,
                "tags": meta.get("tags", []),
                "summary": meta.get("summary", ""),
                "content": parts[2].strip(),
            }
        )
    return articles


def _when(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


async def _load_all(session: AsyncSession) -> dict[str, int]:
    profiles = ProfileRepository(session)
    for email, name, role in DEMO_PROFILES:
        await profiles.create(
            id=seed_id("profile", email), email=email, full_name=name, role=role
        )

    customers = load_json("customers.json")
    ids = {c["key"]: seed_id("customer", c["key"]) for c in customers}
    names = {c["key"]: c["name"] for c in customers}
    customer_repo = CustomerRepository(session)
    memory_repo = CustomerMemoryRepository(session)
    for c in customers:
        await customer_repo.create(
            id=ids[c["key"]],
            created_at=_when(c["created_at"]),
            **{
                k: c[k]
                for k in (
                    "name", "email", "company", "plan_name", "status", "region", "lifetime_value"
                )
            },
        )
        for note in c.get("memory_notes", []):
            await memory_repo.create(
                id=seed_id("memory", f"{c['key']}:{note['content']}"),
                customer_id=ids[c["key"]],
                **note,
            )

    subscriptions = load_json("subscriptions.json")
    for s in subscriptions:
        values = {k: v for k, v in s.items() if k != "customer"}
        values["renews_at"] = _when(values["renews_at"])
        await SubscriptionRepository(session).create(
            id=seed_id("subscription", s["customer"]), customer_id=ids[s["customer"]], **values
        )

    workspaces = load_json("workspaces.json")
    for w in workspaces:
        await WorkspaceRepository(session).create(
            id=seed_id("workspace", f"{w['customer']}:{w['name']}"),
            customer_id=ids[w["customer"]],
            name=w["name"],
            members=w["member_count"],
            settings={
                k: v for k, v in w.items() if k not in {"customer", "name", "member_count"}
            },
        )

    products = load_json("products.json")
    for p in products:
        await ProductRepository(session).create(id=seed_id("product", p["name"]), **p)

    incidents = load_json("incidents.json")
    for i in incidents:
        await IncidentRepository(session).create(
            id=seed_id("incident", i["key"]),
            title=i["title"],
            service=i["service"],
            status=i["status"],
            impact=i["impact"],
            started_at=_when(i["started_at"]),
            resolved_at=_when(i["resolved_at"]),
        )

    articles = load_articles()
    for a in articles:
        await ArticleRepository(session).create(id=seed_id("article", a["slug"]), **a)

    tickets = load_json("tickets.json")
    for t in tickets:
        ticket_id = seed_id("ticket", t["ticket_number"])
        created = _when(t["created_at"])
        await TicketRepository(session).create(
            id=ticket_id,
            ticket_number=t["ticket_number"],
            customer_id=ids[t["customer"]],
            subject=t["subject"],
            body=t["body"],
            channel=t["channel"],
            tags=t["tags"],
            created_at=created,
            updated_at=created,
        )
        await TicketMessageRepository(session).create(
            id=seed_id("message", t["ticket_number"]),
            ticket_id=ticket_id,
            role="customer",
            author_name=names[t["customer"]],
            body=t["body"],
            created_at=created,
            updated_at=created,
        )

    return {
        "profiles": len(DEMO_PROFILES),
        "customers": len(customers),
        "subscriptions": len(subscriptions),
        "workspaces": len(workspaces),
        "products": len(products),
        "incidents": len(incidents),
        "articles": len(articles),
        "tickets": len(tickets),
    }


async def bootstrap_demo_data() -> dict[str, int] | None:
    """Seed once. Returns row counts, or ``None`` when skipped.

    Skipped unless ``DEMO_MODE`` is on, and when any customer already exists. The whole load
    is one transaction, so a failure leaves the database empty.
    """
    if not get_settings().demo_mode:
        logger.info("demo seed skipped: DEMO_MODE is off")
        return None
    async with session_scope() as session:
        if await CustomerRepository(session).count():
            logger.info("demo seed skipped: database is not empty")
            return None
        counts = await _load_all(session)
    logger.info("demo data loaded", extra={"counts": counts})
    return counts


async def _main() -> None:
    setup_logging()
    try:
        await create_tables()
        await bootstrap_demo_data()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
