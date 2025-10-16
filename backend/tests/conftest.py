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

    Uses synchronous psycopg (psycopg3) connection to avoid async event loop conflicts
    during pytest session initialization. TRUNCATE CASCADE for fast cleanup.
    """
    import os
    import psycopg

    # Use synchronous connection to avoid event loop conflicts
    # Get connection params from environment or use test defaults
    db_host = os.getenv('TEST_DB_HOST', 'test-db')
    db_port = int(os.getenv('TEST_DB_PORT', '5432'))
    db_user = os.getenv('TEST_DB_USER', 'test_user')
    db_password = os.getenv('TEST_DB_PASSWORD', 'test_pass')
    db_name = os.getenv('TEST_DB_NAME', 'reddit_scanner_test')

    conn = psycopg.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        dbname=db_name
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
            """
            CREATE TABLE IF NOT EXISTS beta_feedback (
                id UUID PRIMARY KEY,
                task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                satisfaction INTEGER NOT NULL CHECK (satisfaction >= 1 AND satisfaction <= 5),
                missing_communities TEXT[] NOT NULL DEFAULT '{}',
                comments TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_beta_feedback_task_id ON beta_feedback(task_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_beta_feedback_user_id ON beta_feedback(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_beta_feedback_created_at ON beta_feedback(created_at)"
        )
        cursor.execute(
            "TRUNCATE TABLE community_import_history, beta_feedback, community_pool, pending_communities, reports, analyses, tasks, users RESTART IDENTITY CASCADE"
        )
    finally:
        cursor.close()
        conn.close()



# Ensure clean tables for each test as well to avoid cross-test coupling
@pytest.fixture(scope="function", autouse=True)
def truncate_tables_between_tests() -> None:
    import os
    import psycopg

    # Get connection params from environment or use test defaults
    db_host = os.getenv('TEST_DB_HOST', 'test-db')
    db_port = int(os.getenv('TEST_DB_PORT', '5432'))
    db_user = os.getenv('TEST_DB_USER', 'test_user')
    db_password = os.getenv('TEST_DB_PASSWORD', 'test_pass')
    db_name = os.getenv('TEST_DB_NAME', 'reddit_scanner_test')

    conn = psycopg.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        dbname=db_name
    )
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        cursor.execute(
            "TRUNCATE TABLE beta_feedback, community_pool, pending_communities RESTART IDENTITY CASCADE"
        )
    finally:
        cursor.close()
        conn.close()


# For the community import tests module, reset history once at module start so tests can assert cumulative history
@pytest.fixture(scope="module", autouse=True)
def reset_history_for_import_module(request: pytest.FixtureRequest) -> None:
    module_file = getattr(request.module, "__file__", "")
    if module_file.endswith("test_community_import.py"):
        import os
        import psycopg

        # Get connection params from environment or use test defaults
        db_host = os.getenv('TEST_DB_HOST', 'test-db')
        db_port = int(os.getenv('TEST_DB_PORT', '5432'))
        db_user = os.getenv('TEST_DB_USER', 'test_user')
        db_password = os.getenv('TEST_DB_PASSWORD', 'test_pass')
        db_name = os.getenv('TEST_DB_NAME', 'reddit_scanner_test')

        conn = psycopg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        conn.autocommit = True
        cursor = conn.cursor()
        try:
            cursor.execute("TRUNCATE TABLE community_import_history RESTART IDENTITY CASCADE")
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
