from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.models.analysis import Analysis
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel, User


def _dsn_for_user(user: str) -> str:
    raw = os.environ.get("DATABASE_URL") or "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test"
    raw = raw.replace("+asyncpg", "").replace("+psycopg", "")
    parsed = urlparse(raw)
    # Keep host/port/dbname and only swap user info; tests run on trusted local DBs.
    netloc = parsed.hostname or "localhost"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.password:
        netloc = f"{user}:{parsed.password}@{netloc}"
    else:
        netloc = f"{user}@{netloc}"
    return urlunparse((parsed.scheme or "postgresql", netloc, parsed.path, "", "", ""))


@pytest.fixture(scope="module", autouse=True)
def _ensure_rss_app_privileges() -> None:
    """
    Ensure the test DB can simulate the production app role (rss_app).

    We intentionally test RLS behavior using a non-owner role; postgres owner bypasses RLS.
    """
    # Use the configured test DB user (may not be 'postgres' in CI).
    parsed = urlparse((os.environ.get("DATABASE_URL") or "").replace("+asyncpg", "").replace("+psycopg", ""))
    admin_user = parsed.username or "postgres"
    dsn = _dsn_for_user(admin_user)
    conn = psycopg.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'rss_app' LIMIT 1")
            exists = cur.fetchone() is not None
            password = parsed.password
            if not exists:
                if password:
                    cur.execute("CREATE ROLE rss_app LOGIN PASSWORD %s", (password,))
                else:
                    cur.execute("CREATE ROLE rss_app LOGIN")
            elif password:
                cur.execute("ALTER ROLE rss_app WITH LOGIN PASSWORD %s", (password,))
            cur.execute("GRANT USAGE ON SCHEMA public TO rss_app")
            cur.execute("GRANT SELECT ON TABLE public.tasks TO rss_app")
            cur.execute("GRANT SELECT ON TABLE public.analyses TO rss_app")
    finally:
        conn.close()


def test_rls_policy_does_not_raise_when_context_missing() -> None:
    """
    Contract A (DB layer):
    Even if app.current_user_id isn't set, tenant policies must NOT crash the request.
    """
    dsn = _dsn_for_user("rss_app")
    conn = psycopg.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM analyses")
            count = int(cur.fetchone()[0] or 0)
            # No context should default to "see nothing", not "500".
            assert count >= 0
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_rls_session_injects_current_user_id_for_rss_app(
    db_session: AsyncSession,
) -> None:
    user = User(
        email=f"rls-{uuid4().hex}@example.com",
        password_hash=hash_password("testpass123"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="RLS context injection verification task",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    analysis = Analysis(
        task_id=task.id,
        insights={
            "pain_points": [],
            "competitors": [],
            "opportunities": [],
        },
        sources={
            "communities": [],
            "posts_analyzed": 0,
            "cache_hit_rate": 0.0,
        },
        analysis_version=1,
    )
    db_session.add(analysis)
    await db_session.commit()

    from app.core.tenant_context import set_current_user_id, unset_current_user_id

    rss_engine = create_async_engine(_dsn_for_user("rss_app").replace("postgresql://", "postgresql+asyncpg://"))
    Session = async_sessionmaker(rss_engine, class_=AsyncSession, expire_on_commit=False)
    try:
        unset_current_user_id()
        async with Session() as rss_session:
            result = await rss_session.execute(select(Analysis.id).limit(1))
            assert result.scalar_one_or_none() is None

        set_current_user_id(user.id)
        async with Session() as rss_session:
            result = await rss_session.execute(select(Analysis.id).where(Analysis.task_id == task.id))
            assert result.scalar_one_or_none() == analysis.id

        set_current_user_id(UUID("00000000-0000-0000-0000-000000000000"))
        async with Session() as rss_session:
            result = await rss_session.execute(select(Analysis.id).where(Analysis.task_id == task.id))
            assert result.scalar_one_or_none() is None
    finally:
        await rss_engine.dispose()
