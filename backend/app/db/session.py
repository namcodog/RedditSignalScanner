"""
Async SQLAlchemy session utilities for Celery tasks and API handlers.

This module provides a shared async session factory that pulls the
``DATABASE_URL`` from environment variables. Celery workers run in a
sync context, so helpers expose ``asynccontextmanager`` wrappers that
can be invoked via ``asyncio.run`` within Celery tasks.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_scanner"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _create_engine() -> AsyncEngine:
    return create_async_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        future=True,
        # Use NullPool to avoid event loop conflicts across tests where pools
        # hold connections created in a different loop.
        poolclass=NullPool,
        echo=False,
    )


engine: AsyncEngine = _create_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


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
