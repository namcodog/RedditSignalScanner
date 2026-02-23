"""
Async SQLAlchemy session utilities for Celery tasks and API handlers.

This module provides a shared async session factory that pulls the
``DATABASE_URL`` from environment variables. Celery workers run in a
sync context, so helpers expose ``asynccontextmanager`` wrappers that
can be invoked via ``asyncio.run`` within Celery tasks.
"""

from __future__ import annotations

import os
from urllib.parse import quote_plus
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.core.tenant_context import resolve_current_user_id_for_rls
from app.db.database_guard import validate_database_target

def _default_database_url() -> str:
    driver = os.getenv("POSTGRES_DRIVER", "postgresql+asyncpg")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "reddit_signal_scanner_dev")
    return f"{driver}://{user}:{password}@{host}:{port}/{name}"


DEFAULT_DATABASE_URL = _default_database_url()
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
validate_database_target(DATABASE_URL)
USE_NULL_POOL = os.getenv("SQLALCHEMY_DISABLE_POOL", "0") == "1"
POOL_SIZE = int(os.getenv("SQLALCHEMY_POOL_SIZE", "2"))
MAX_OVERFLOW = int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "0"))
POOL_TIMEOUT = int(os.getenv("SQLALCHEMY_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "1800"))


def _create_engine() -> AsyncEngine:
    engine_kwargs: dict[str, object] = {
        "pool_pre_ping": True,
        "future": True,
        "echo": False,
    }

    if USE_NULL_POOL:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = POOL_SIZE
        engine_kwargs["max_overflow"] = MAX_OVERFLOW
        engine_kwargs["pool_timeout"] = POOL_TIMEOUT
        engine_kwargs["pool_recycle"] = POOL_RECYCLE

    return create_async_engine(
        DATABASE_URL,
        **engine_kwargs,
    )


engine: AsyncEngine = _create_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@event.listens_for(Session, "after_begin")
def _inject_rls_session_context(
    session: Session, transaction: object, connection: object
) -> None:
    # RLS context only applies to Postgres; skip other dialects (e.g. sqlite in unit tests).
    dialect = getattr(connection, "dialect", None)
    if getattr(dialect, "name", "") != "postgresql":
        return
    user_id = resolve_current_user_id_for_rls()
    try:
        connection.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": user_id},
        )
    except Exception:
        # Defensive: never crash the caller because of context injection.
        # DB policies should still be missing_ok=true (deny-by-default) after Phase 103.
        return


@asynccontextmanager
async def get_session_context() -> AsyncIterator[AsyncSession]:
    """Provide a transactional context that commits or rolls back automatically."""
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


# Backwards compatible alias
session_scope = get_session_context


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
