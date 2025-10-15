from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable, Tuple

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    """Ensure pytest-asyncio runs in auto mode for consistent loop handling."""
    config.option.asyncio_mode = "auto"


def pytest_sessionstart(session: pytest.Session) -> None:
    """Diagnostic hook to ensure pytest session starts printing immediately."""
    print("PYTEST SESSION START (diagnostic)", flush=True)


@pytest.fixture(scope="function")
def anyio_backend() -> str:
    """Force anyio to use asyncio backend so fixtures share the same loop."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def reset_database() -> None:
    """
    Ensure the core tables start clean for deterministic metrics.

    Uses synchronous psycopg2 connection to avoid async event loop conflicts
    during pytest session initialization. TRUNCATE CASCADE for fast cleanup.
    """
    import psycopg2

    # Use synchronous connection to avoid event loop conflicts
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='reddit_scanner'
    )
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            ALTER TABLE community_pool
            ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'medium'
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS community_import_history (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                uploaded_by VARCHAR(255) NOT NULL,
                uploaded_by_user_id UUID NOT NULL,
                dry_run BOOLEAN NOT NULL DEFAULT FALSE,
                status VARCHAR(20) NOT NULL,
                total_rows INTEGER NOT NULL DEFAULT 0,
                valid_rows INTEGER NOT NULL DEFAULT 0,
                invalid_rows INTEGER NOT NULL DEFAULT 0,
                duplicate_rows INTEGER NOT NULL DEFAULT 0,
                imported_rows INTEGER NOT NULL DEFAULT 0,
                error_details JSONB NULL,
                summary_preview JSONB NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_community_import_history_created
            ON community_import_history(created_at)
            """
        )
        cursor.execute(
            "TRUNCATE TABLE community_import_history, community_pool, pending_communities, reports, analyses, tasks, users RESTART IDENTITY CASCADE"
        )
    finally:
        cursor.close()
        conn.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide an isolated AsyncSession per test."""
    from app.db.session import SessionFactory

    async with SessionFactory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP client fixture leveraging dependency override to inject fresh sessions."""
    from app.db.session import SessionFactory, get_session, engine
    from app.main import app

    # Dispose engine before each test to avoid event loop conflicts
    # This ensures each test gets a fresh connection pool bound to the current event loop
    await engine.dispose()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with SessionFactory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client

    app.dependency_overrides.pop(get_session, None)

    # Dispose engine after each test to clean up connections
    await engine.dispose()


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function")
async def token_factory(
    client: AsyncClient,
) -> Callable[..., Awaitable[Tuple[str, str]]]:
    """Create users and return (access_token, user_id) tuples for integration tests."""

    async def _create(password: str = "SecurePass123!", email: str | None = None) -> Tuple[str, str]:
        email_address = email or f"auth-int-{uuid.uuid4().hex}@example.com"

        register_resp = await client.post(
            "/api/auth/register",
            json={"email": email_address, "password": password},
        )
        assert register_resp.status_code == 201

        login_resp = await client.post(
            "/api/auth/login",
            json={"email": email_address, "password": password},
        )
        assert login_resp.status_code == 200
        payload = login_resp.json()
        return payload["access_token"], payload["user"]["id"]

    return _create


@pytest_asyncio.fixture(scope="function")
async def auth_token(token_factory: Callable[[str], Awaitable[Tuple[str, str]]]) -> str:
    """Provide a ready-to-use access token for authenticated API calls."""
    token, _ = await token_factory()
    return token
