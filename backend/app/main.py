"""FastAPI entrypoint. Middleware order (outermost last): CORS -> RequestId -> ..."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health
from app.core.config import get_settings
from app.core.database import create_tables, dispose_engine
from app.core.logging import setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import HEADER, RequestIdMiddleware
from app.services.seed_service import bootstrap_demo_data


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create tables, then load demo data into an empty database (DEMO_MODE only)."""
    await create_tables()
    await bootstrap_demo_data()
    try:
        yield
    finally:
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    app = FastAPI(title="CloudDesk Support API", version="0.1.0", lifespan=lifespan)

    # add_middleware prepends; last added = outermost. Order: CORS → RequestId → RateLimit → app.
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[HEADER],
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    return app


app = create_app()
