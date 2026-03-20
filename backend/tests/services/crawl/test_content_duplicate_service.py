from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.crawl.content_duplicate_service import (
    ContentDuplicateLookupDeps,
    ContentDuplicateLookupInput,
    find_content_duplicate,
)


@pytest.mark.asyncio
async def test_find_content_duplicate_returns_none_when_hash_unavailable() -> None:
    execute_query = AsyncMock()

    result = await find_content_duplicate(
        lookup_input=ContentDuplicateLookupInput(
            subreddit="r/test",
            title="Title",
            body="Body",
        ),
        deps=ContentDuplicateLookupDeps(
            text_norm_hash_available=AsyncMock(return_value=False),
            execute_query=execute_query,
        ),
    )

    assert result is None
    execute_query.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_content_duplicate_returns_source_post_id_when_found() -> None:
    async def _execute_query(*_args, **_kwargs):
        return SimpleNamespace(first=lambda: ("existing-post",))

    result = await find_content_duplicate(
        lookup_input=ContentDuplicateLookupInput(
            subreddit="r/test",
            title="Title",
            body="Body",
        ),
        deps=ContentDuplicateLookupDeps(
            text_norm_hash_available=AsyncMock(return_value=True),
            execute_query=_execute_query,
        ),
    )

    assert result == "existing-post"
