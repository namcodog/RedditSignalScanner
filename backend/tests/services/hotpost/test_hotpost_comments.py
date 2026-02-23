from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.services.hotpost.service import HotpostService


class _FakeRedditClient:
    async def fetch_post_comments(self, *_args, **_kwargs):
        return [
            {"body": "x" * 500, "score": 10},
            {"body": "y" * 450, "score": 5},
            {"body": "z" * 10, "score": 1},
            {"body": "extra", "score": 0},
        ]


@pytest.mark.asyncio
async def test_fetch_comments_truncates_and_limits() -> None:
    settings = Settings(environment="test", allow_mock_fallback=True)
    service = HotpostService(
        settings=settings,
        db=AsyncMock(),
        redis_client=AsyncMock(),
        reddit_client=_FakeRedditClient(),
    )

    async def _noop(*_args, **_kwargs):
        return None

    service._acquire_rate_budget = _noop  # type: ignore[method-assign]

    comments = await service._fetch_comments("abc")

    assert len(comments) == 3
    assert len(comments[0]["body"]) == 400
    assert len(comments[1]["body"]) == 400
    assert len(comments[2]["body"]) == 10
