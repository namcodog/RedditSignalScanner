from __future__ import annotations

import pytest

from app.db.session import engine


@pytest.fixture(autouse=True)
async def dispose_async_engine_after_test() -> None:
    """Ensure asyncpg connections do not leak across integration tests."""
    try:
        yield
    finally:
        await engine.dispose()
