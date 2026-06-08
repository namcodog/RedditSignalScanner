from __future__ import annotations

import pytest

from app.services.infrastructure.reddit_client import RedditAPIError, RedditPost
from scripts.hotpost.reddit_preflight import run_reddit_preflight


pytestmark = pytest.mark.asyncio


class _PreflightReddit:
    def __init__(self, *, fail_auth: Exception | None = None, fail_listing: Exception | None = None) -> None:
        self.fail_auth = fail_auth
        self.fail_listing = fail_listing
        self.calls: list[str] = []

    async def __aenter__(self):
        self.calls.append("enter")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.calls.append("exit")
        return None

    async def authenticate(self) -> None:
        self.calls.append("authenticate")
        if self.fail_auth is not None:
            raise self.fail_auth

    async def fetch_subreddit_posts(self, subreddit: str, **_kwargs):
        self.calls.append(f"fetch:{subreddit}")
        if self.fail_listing is not None:
            raise self.fail_listing
        return (
            [
                RedditPost(
                    id="p1",
                    title="ok",
                    selftext="",
                    score=1,
                    num_comments=1,
                    created_utc=1.0,
                    subreddit=subreddit,
                    author="u",
                    url="https://reddit.com/p1",
                    permalink="/r/OpenAI/comments/p1",
                )
            ],
            None,
        )


async def test_reddit_preflight_passes_auth_and_minimal_listing() -> None:
    seen: dict[str, _PreflightReddit] = {}

    def factory() -> _PreflightReddit:
        seen["client"] = _PreflightReddit()
        return seen["client"]

    result = await run_reddit_preflight(reddit_factory=factory)

    assert result["ok"] is True
    assert result["checks"]["oauth_token"] == "ok"
    assert result["checks"]["minimal_listing"] == "ok"
    assert seen["client"].calls == ["enter", "authenticate", "fetch:OpenAI", "exit"]


async def test_reddit_preflight_fails_before_full_collect_when_oauth_is_down() -> None:
    def factory() -> _PreflightReddit:
        return _PreflightReddit(fail_auth=RedditAPIError("Reddit API connection failed: token endpoint"))

    result = await run_reddit_preflight(reddit_factory=factory)

    assert result["ok"] is False
    assert result["checks"]["oauth_token"] == "failed"
    assert result["checks"]["minimal_listing"] == "skipped"
    assert "token endpoint" in result["error"]
