from __future__ import annotations

import os
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import psycopg
import pytest

from app.db.rls_sanity import verify_rls_startup_sanity


def _base_dsn() -> str:
    raw = os.environ.get("DATABASE_URL") or "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test"
    raw = raw.replace("+asyncpg", "").replace("+psycopg", "")
    return raw


def _dsn_for_user(user: str) -> tuple[str, str | None]:
    parsed = urlparse(_base_dsn())
    netloc = parsed.hostname or "localhost"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    password = parsed.password
    if password:
        netloc = f"{user}:{password}@{netloc}"
    else:
        netloc = f"{user}@{netloc}"
    return (
        urlunparse((parsed.scheme or "postgresql", netloc, parsed.path, "", "", "")),
        password,
    )


@pytest.fixture(scope="module", autouse=True)
def _ensure_rss_app_role() -> None:
    dsn, password = _dsn_for_user(urlparse(_base_dsn()).username or "postgres")
    conn = psycopg.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'rss_app' LIMIT 1")
            exists = cur.fetchone() is not None
            if not exists:
                if password:
                    cur.execute("CREATE ROLE rss_app LOGIN PASSWORD %s", (password,))
                else:
                    cur.execute("CREATE ROLE rss_app LOGIN")
            elif password:
                # Ensure rss_app can connect in password-based CI environments.
                cur.execute("ALTER ROLE rss_app WITH LOGIN PASSWORD %s", (password,))
            cur.execute("GRANT USAGE ON SCHEMA public TO rss_app")
            # Sanity check should be able to touch RLS-protected tables.
            cur.execute("GRANT SELECT ON TABLE public.analyses TO rss_app")
            cur.execute("GRANT SELECT ON TABLE public.tasks TO rss_app")
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_rls_startup_sanity_passes_for_rss_app() -> None:
    dsn, _ = _dsn_for_user("rss_app")
    dsn = dsn.replace("postgresql://", "postgresql+asyncpg://")
    result = await verify_rls_startup_sanity(
        database_url=dsn,
        required_user="rss_app",
    )
    assert result["db_user"] == "rss_app"


@pytest.mark.asyncio
async def test_rls_startup_sanity_fails_when_user_mismatch() -> None:
    dsn, _ = _dsn_for_user(urlparse(_base_dsn()).username or "postgres")
    dsn = dsn.replace("postgresql://", "postgresql+asyncpg://")
    with pytest.raises(RuntimeError):
        await verify_rls_startup_sanity(
            database_url=dsn,
            required_user="rss_app",
            probe_user_id=uuid4(),
        )
