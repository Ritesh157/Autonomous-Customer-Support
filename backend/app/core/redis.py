"""Redis / fakeredis client factory (N2).

Returns an async-compatible Redis client.

- ``USE_FAKE_REDIS=true`` or empty ``REDIS_URL`` → ``fakeredis.aioredis.FakeRedis``
  (in-process, no network, used by tests and ``DEMO_MODE``).
- ``REDIS_URL`` set → real ``redis.asyncio`` client backed by that URL.

Callers receive a new client instance each call; the middleware holds the
reference for the app's lifetime so shared state is preserved across requests.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_redis():
    """Return an async Redis client appropriate for the current configuration."""
    settings = get_settings()
    if settings.use_fake_redis or not settings.redis_url:
        import fakeredis.aioredis as _fakeredis  # type: ignore[import]

        logger.debug("using fakeredis (USE_FAKE_REDIS=%s)", settings.use_fake_redis)
        return _fakeredis.FakeRedis(decode_responses=False)

    import redis.asyncio as _aioredis  # type: ignore[import]

    logger.debug("connecting to Redis at %s", settings.redis_url)
    return _aioredis.from_url(settings.redis_url, decode_responses=False)
