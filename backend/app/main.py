"""FastAPI entrypoint. Middleware order (outermost last): CORS -> RequestId -> ..."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.middleware.request_id import HEADER, RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    app = FastAPI(title="CloudDesk Support API", version="0.1.0")

    # add_middleware prepends, so the last added is outermost: RequestId first, CORS last.
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
    return app


app = create_app()
