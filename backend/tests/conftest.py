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


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.

    Based on exa-code best practices for pytest-asyncio:
    - Use session scope to avoid creating multiple event loops
    - Properly close the loop after all tests complete
    - Prevents "attached to a different loop" errors
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


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
    # Default to localhost for local development, test-db for CI/Docker
    db_host = os.getenv('TEST_DB_HOST', 'localhost')
    db_port = int(os.getenv('TEST_DB_PORT', '5432'))
    db_user = os.getenv('TEST_DB_USER', 'postgres')
    db_password = os.getenv('TEST_DB_PASSWORD', '')
    db_name = os.getenv('TEST_DB_NAME', 'reddit_scanner')

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
def truncate_tables_between_tests(request: pytest.FixtureRequest) -> None:
    import os
    import psycopg

    # Skip truncation for integration tests (they need real data)
    if request.node.get_closest_marker("integration"):
        return

    # Skip truncation for e2e tests (they need real data)
    if request.node.get_closest_marker("e2e"):
        return

    # Get connection params from environment or use test defaults
    # Default to localhost for local development, test-db for CI/Docker
    db_host = os.getenv('TEST_DB_HOST', 'localhost')
    db_port = int(os.getenv('TEST_DB_PORT', '5432'))
    db_user = os.getenv('TEST_DB_USER', 'postgres')
    db_password = os.getenv('TEST_DB_PASSWORD', '')
    db_name = os.getenv('TEST_DB_NAME', 'reddit_scanner')

    # For test_community_import.py, preserve history between tests
    module_file = getattr(request.module, "__file__", "")
    preserve_history = module_file.endswith("test_community_import.py")

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
        if preserve_history:
            # Don't truncate community_import_history for test_community_import.py
            cursor.execute(
                "TRUNCATE TABLE beta_feedback, community_pool, pending_communities RESTART IDENTITY CASCADE"
            )
        else:
            cursor.execute(
                "TRUNCATE TABLE beta_feedback, community_pool, pending_communities, community_import_history RESTART IDENTITY CASCADE"
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
        # Default to localhost for local development, test-db for CI/Docker
        db_host = os.getenv('TEST_DB_HOST', 'localhost')
        db_port = int(os.getenv('TEST_DB_PORT', '5432'))
        db_user = os.getenv('TEST_DB_USER', 'postgres')
        db_password = os.getenv('TEST_DB_PASSWORD', '')
        db_name = os.getenv('TEST_DB_NAME', 'reddit_scanner')

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


@pytest.fixture(scope="function")
def seeded_cache(monkeypatch):
    """
    Provide a CacheManager with pre-populated test data for analysis_engine tests.

    Based on exa-code best practices:
    - Use fakeredis to avoid external Redis dependency
    - Seed with realistic test data matching test assertions
    - Ensure 90%+ cache hit rate as per PRD-03 §1.4
    - Clear Reddit credentials to force cache-only mode
    """
    try:
        import fakeredis
    except ImportError:
        pytest.skip("fakeredis not installed")

    from app.services.cache_manager import CacheManager
    from app.services.reddit_client import RedditPost
    from app.core.config import Settings, get_settings
    import app.services.analysis_engine as analysis_engine_module

    # Monkeypatch get_settings to return Settings without Reddit credentials
    # This forces _build_data_collection_service to return None, ensuring cache-only mode
    original_get_settings = get_settings

    def mock_get_settings() -> Settings:
        settings = original_get_settings()
        # Create a new Settings instance with empty Reddit credentials
        return Settings(
            database_url=settings.database_url,
            cors_origins_raw=settings.cors_origins_raw,
            jwt_secret=settings.jwt_secret,
            jwt_algorithm=settings.jwt_algorithm,
            environment=settings.environment,
            reddit_client_id="",  # Empty to force cache-only mode
            reddit_client_secret="",  # Empty to force cache-only mode
            reddit_user_agent=settings.reddit_user_agent,
            reddit_rate_limit=settings.reddit_rate_limit,
            reddit_rate_limit_window_seconds=settings.reddit_rate_limit_window_seconds,
            reddit_request_timeout_seconds=settings.reddit_request_timeout_seconds,
            reddit_max_concurrency=settings.reddit_max_concurrency,
            reddit_cache_redis_url=settings.reddit_cache_redis_url,
            reddit_cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
            admin_emails_raw=settings.admin_emails_raw,
        )

    monkeypatch.setattr(analysis_engine_module, "get_settings", mock_get_settings)

    # Create fake Redis client
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=False)
    cache = CacheManager(redis_client=fake_redis, cache_ttl_seconds=3600)

    # Seed data for all communities in COMMUNITY_CATALOGUE
    # Based on exa-code best practices: seed all possible communities that might be selected
    # Need enough posts to generate 5+ pain_points, 3+ competitors, 3+ opportunities

    # Template posts with pain points, competitors, and opportunities
    # Need 5+ distinct pain points, 3+ competitors, 3+ opportunities
    template_posts = [
        RedditPost(
            id="{subreddit}-1",
            title="Users can't stand the slow onboarding workflow",
            selftext="I can't stand how painfully slow the onboarding workflow feels for research teams.",
            score=180,
            num_comments=20,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/1",
            permalink="/{subreddit}/comments/1",
        ),
        RedditPost(
            id="{subreddit}-2",
            title="Notion vs Evernote for automation reports",
            selftext="Notion vs Evernote showdown as an alternative to automate reporting flows.",
            score=140,
            num_comments=12,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/2",
            permalink="/{subreddit}/comments/2",
        ),
        RedditPost(
            id="{subreddit}-3",
            title="Looking for an automation tool that would pay for itself",
            selftext="Looking for an automation tool that would pay for itself with weekly insight digests.",
            score=120,
            num_comments=8,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/3",
            permalink="/{subreddit}/comments/3",
        ),
        RedditPost(
            id="{subreddit}-4",
            title="Why is export still so confusing for product teams?",
            selftext="Why is export so confusing and unreliable even for product teams working on automation?",
            score=160,
            num_comments=18,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/4",
            permalink="/{subreddit}/comments/4",
        ),
        RedditPost(
            id="{subreddit}-5",
            title="Problem with automation quality in customer reports",
            selftext="Problem with automation quality: the generated reports feel confusing and frustrating for stakeholders.",
            score=150,
            num_comments=14,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/5",
            permalink="/{subreddit}/comments/5",
        ),
        RedditPost(
            id="{subreddit}-6",
            title="Struggling with manual data collection every week",
            selftext="Struggling with manual data collection every week - it's eating up hours that could be spent on analysis.",
            score=135,
            num_comments=16,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/6",
            permalink="/{subreddit}/comments/6",
        ),
        RedditPost(
            id="{subreddit}-7",
            title="Roam Research vs Obsidian for note organization",
            selftext="Roam Research vs Obsidian comparison for organizing research notes and insights.",
            score=125,
            num_comments=11,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/7",
            permalink="/{subreddit}/comments/7",
        ),
        RedditPost(
            id="{subreddit}-8",
            title="Need better collaboration features for team research",
            selftext="Need better collaboration features - current tools make it hard for teams to share insights in real-time.",
            score=145,
            num_comments=13,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/8",
            permalink="/{subreddit}/comments/8",
        ),
        RedditPost(
            id="{subreddit}-9",
            title="Would pay premium for AI-powered research summaries",
            selftext="Would pay premium for AI-powered research summaries that save time on literature reviews.",
            score=155,
            num_comments=17,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/9",
            permalink="/{subreddit}/comments/9",
        ),
        RedditPost(
            id="{subreddit}-10",
            title="Seeking alternative to manual note-taking for research",
            selftext="Seeking alternative to manual note-taking - need something that can automatically summarize findings.",
            score=130,
            num_comments=15,
            created_utc=1.0,
            subreddit="{subreddit}",
            author="tester",
            url="https://reddit.com/{subreddit}/10",
            permalink="/{subreddit}/comments/10",
        ),
    ]

    # All communities from COMMUNITY_CATALOGUE that might be selected
    communities = [
        "r/startups",
        "r/Entrepreneur",
        "r/ProductManagement",
        "r/SaaS",
        "r/marketing",
        "r/technology",
        "r/artificial",
        "r/userexperience",
        "r/smallbusiness",
        "r/GrowthHacking",
    ]

    seed_posts = {}
    for community in communities:
        # Create posts for each community by replacing {subreddit} placeholder
        community_posts = []
        for template in template_posts:
            post_dict = {
                "id": template.id.replace("{subreddit}", community),
                "title": template.title,
                "selftext": template.selftext,
                "score": template.score,
                "num_comments": template.num_comments,
                "created_utc": template.created_utc,
                "subreddit": community,
                "author": template.author,
                "url": template.url.replace("{subreddit}", community),
                "permalink": template.permalink.replace("{subreddit}", community),
            }
            community_posts.append(RedditPost(**post_dict))
        seed_posts[community] = community_posts

    # Legacy: keep original detailed posts for r/artificial for backward compatibility
    seed_posts["r/artificial"] = [
            RedditPost(
                id="r/artificial-1",
                title="Users can't stand the slow onboarding workflow",
                selftext="I can't stand how painfully slow the onboarding workflow feels for research teams.",
                score=180,
                num_comments=20,
                created_utc=1.0,
                subreddit="r/artificial",
                author="tester",
                url="https://reddit.com/r/artificial/1",
                permalink="/r/artificial/comments/1",
            ),
            RedditPost(
                id="r/artificial-2",
                title="Notion vs Evernote for automation reports",
                selftext="Notion vs Evernote showdown as an alternative to automate reporting flows.",
                score=140,
                num_comments=12,
                created_utc=1.0,
                subreddit="r/artificial",
                author="tester",
                url="https://reddit.com/r/artificial/2",
                permalink="/r/artificial/comments/2",
            ),
            RedditPost(
                id="r/artificial-3",
                title="Looking for an automation tool that would pay for itself",
                selftext="Looking for an automation tool that would pay for itself with weekly insight digests.",
                score=120,
                num_comments=8,
                created_utc=1.0,
                subreddit="r/artificial",
                author="tester",
                url="https://reddit.com/r/artificial/3",
                permalink="/r/artificial/comments/3",
            ),
        ]

    # Populate cache
    for subreddit, posts in seed_posts.items():
        cache.set_cached_posts(subreddit, posts)

    return cache
