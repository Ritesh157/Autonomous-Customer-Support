"""Health probes. Unprefixed (not under /api/v1)."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
async def live() -> dict[str, str]:
    """Liveness: no I/O, used by container probes."""
    return {"status": "ok"}


def readiness_checks(s: Settings) -> dict[str, str]:
    """Configuration-level checks only; no connections are opened yet.

    Details never contain URLs, passwords or API keys.
    """
    checks: dict[str, str] = {}
    checks["database"] = "ok" if s.database_url else "missing DATABASE_URL"
    checks["redis"] = "ok" if (s.redis_url or s.use_fake_redis or s.demo_mode) else "missing REDIS_URL"
    if s.vector_store == "memory":
        checks["vector_store"] = "ok"
    elif s.vector_store == "qdrant":
        checks["vector_store"] = "ok" if s.qdrant_url else "missing QDRANT_URL"
    else:
        checks["vector_store"] = "unknown VECTOR_STORE"
    if s.llm_provider == "fake":
        checks["llm"] = "ok"
    else:
        checks["llm"] = "ok" if s.llm_api_key.get_secret_value() else "missing LLM_API_KEY"
    return checks


@router.get("/health/ready")
async def ready() -> JSONResponse:
    checks = readiness_checks(get_settings())
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ready" if ok else "degraded", "checks": checks},
        status_code=200 if ok else 503,
    )
