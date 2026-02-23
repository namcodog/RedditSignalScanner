from __future__ import annotations

import os
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.tenant_context import set_current_user_id, unset_current_user_id


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def should_run_rls_startup_sanity_check(*, environment: str) -> bool:
    """
    Decide whether to run the RLS startup sanity check.

    Human goal:
    - Production/staging: default ON (fail fast if RLS基础设施断了)
    - Dev/test: default OFF (可按需开启)
    """
    override = os.getenv("ENABLE_RLS_STARTUP_SANITY_CHECK", "").strip()
    if override:
        return _truthy(override)
    env = (environment or "").strip().lower()
    if os.getenv("PYTEST_RUNNING") == "1":
        return False
    return env not in {"development", "dev", "test"}


async def verify_rls_startup_sanity(
    *,
    database_url: str,
    required_user: str | None = None,
    probe_user_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Contract A gate (startup sanity):
    - Must NOT crash when querying RLS tables even if app.current_user_id is missing.
    - Must be able to inject app.current_user_id in-session (transaction-scoped).
    - Optionally enforce connecting user == required_user (e.g. rss_app), to avoid postgres "superpower" masking.
    """
    probe = probe_user_id or uuid4()

    engine = create_async_engine(database_url, pool_pre_ping=True, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    db_user = ""
    try:
        # 1) Identify DB user.
        async with engine.connect() as conn:
            db_user = str((await conn.scalar(text("SELECT current_user"))) or "")
            if required_user and db_user.strip() != required_user:
                raise RuntimeError(
                    f"RLS sanity check failed: expected db_user={required_user!r}, got {db_user!r}"
                )

            # 2) DB-layer resilience: query RLS tables without any injected GUC.
            # This must not throw "unrecognized configuration parameter ...".
            await conn.execute(text("SELECT COUNT(*) FROM analyses"))
            await conn.execute(text("SELECT COUNT(*) FROM tasks"))

        # 3) App-layer injection: verify our session hook can set app.current_user_id per transaction.
        set_current_user_id(probe)
        async with Session() as session:
            value = str(
                (await session.scalar(text("SELECT current_setting('app.current_user_id', true)")))
                or ""
            ).strip()
            if value != str(probe):
                raise RuntimeError(
                    "RLS sanity check failed: session did not inject app.current_user_id "
                    f"(expected={probe}, got={value or 'NULL'})"
                )
    finally:
        unset_current_user_id()
        await engine.dispose()

    return {
        "status": "ok",
        "db_user": db_user.strip() or "unknown",
        "probe_user_id": str(probe),
    }


__all__ = [
    "should_run_rls_startup_sanity_check",
    "verify_rls_startup_sanity",
]
