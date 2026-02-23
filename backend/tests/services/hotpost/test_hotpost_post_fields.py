from __future__ import annotations

from unittest.mock import AsyncMock

from app.core.config import Settings
from app.services.hotpost.service import HotpostService
from app.services.reddit_client import RedditPost


def _make_service() -> HotpostService:
    settings = Settings(environment="test", allow_mock_fallback=True)
    return HotpostService(
        settings=settings,
        db=AsyncMock(),
        redis_client=AsyncMock(),
        reddit_client=AsyncMock(),
    )


def test_build_post_includes_heat_score_and_preview() -> None:
    service = _make_service()
    post = RedditPost(
        id="abc",
        title="Test title",
        selftext="x" * 600,
        score=10,
        num_comments=5,
        created_utc=0.0,
        subreddit="r/test",
        author="author",
        url="/r/test/comments/abc",
        permalink="/r/test/comments/abc",
    )
    signals = {"strong": ["broken"], "medium": [], "weak": []}

    hotpost = service._build_post(post, rank=1, signals=signals)

    assert hotpost.heat_score == 20
    assert hotpost.body_preview == "x" * 500
    assert hotpost.reddit_url.startswith("https://www.reddit.com")
