"""Async engine and session factory. One engine per database URL.

SQLite is the demo database; Postgres (``postgresql+asyncpg``) is the cloud one.
"""
# postgresql: Database system is PostgreSQL.
# asyncpg: Use the asyncpg driver to communicate asynchronously with PostgreSQL.


from __future__ import annotations          # This tells Python to postpone evaluating type annotations.

from collections.abc import AsyncIterator   # An asynchronous iterator lets you retrieve items asynchronously.
from contextlib import asynccontextmanager  # This imports a decorator that create an asynchronous context manager using an async generator function.
from functools import lru_cache     # imports a caching decorator. Storing the result of a function. lru_cache stands for Least Recently Used Cache.
from pathlib import Path            # a Python class for working with file and directory paths.

from sqlalchemy import event        # allows you to execute custom Python code when certain database events happen.
from sqlalchemy.engine import make_url  # converts a database connection URL string into a structured SQLAlchemy URL object.
from sqlalchemy.ext.asyncio import (
    AsyncEngine,                    # main connection manager between Python application and the database
    AsyncSession,                   # A session is used to perform database operations.
    async_sessionmaker,             # creates AsyncSession objects. Creates database sessions.
    create_async_engine,            # This is the function used to actually create an asynchronous SQLAlchemy engine.
)

from app.core.config import get_settings
from app.models.entities import Base


@lru_cache
def _engine_for(url: str) -> AsyncEngine:           # helper function
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == "sqlite"   # checks the database type. (sqllite or postgreSQL)
    if is_sqlite and parsed.database and parsed.database != ":memory:":     # database must not be an in-memory database.
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(url, pool_pre_ping=not is_sqlite)
    if is_sqlite:

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:
            cursor = dbapi_connection.cursor()          # Create a database cursor. Used to execute SQL statements
            cursor.execute("PRAGMA foreign_keys=ON")        # Enable foreign key
            cursor.close()

    return engine                                   # function returns the asynchronous engine.


def get_engine() -> AsyncEngine:
    return _engine_for(get_settings().database_url)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Commit on success, roll back on any error. Repositories only flush."""
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def create_tables() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    await get_engine().dispose()
    _engine_for.cache_clear()
