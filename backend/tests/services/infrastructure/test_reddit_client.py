from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import pytest

from app.services.infrastructure.reddit_client import (
    RedditAPIClient,
    RedditAPIError,
    RedditPost,
)


pytestmark = pytest.mark.asyncio


@dataclass
class _StubResponse:
    status: int
    payload: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)

    async def __aenter__(self) -> "_StubResponse":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def json(self) -> Dict[str, Any]:
        return self.payload

    async def text(self) -> str:
        return json.dumps(self.payload)


class _StubSession:
    def __init__(self, responses: Sequence[Any]) -> None:
        self._responses = list(responses)
        self.requests: List[Dict[str, Any]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> _StubResponse:
        if not self._responses:
            raise RedditAPIError(f"Unexpected request: {method} {url}")
        next_item = self._responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        self.requests.append(
            {
                "method": method,
                "url": url,
                "kwargs": kwargs,
            }
        )
        return next_item

    async def close(self) -> None:
        self.closed = True


def _token_response() -> _StubResponse:
    return _StubResponse(
        status=200,
        payload={
            "access_token": "test-token",
            "expires_in": 3600,
            "token_type": "bearer",
        },
    )


def _posts_response(subreddit: str) -> _StubResponse:
    return _StubResponse(
        status=200,
        payload={
            "data": {
                "children": [
                    {
                        "data": {
                            "id": f"{subreddit}-1",
                            "title": f"{subreddit} post",
                            "selftext": "Body",
                            "score": 42,
                            "num_comments": 5,
                            "created_utc": 1700000000.0,
                            "subreddit": subreddit,
                            "author": "tester",
                            "url": f"https://reddit.com/{subreddit}/1",
                            "permalink": f"/r/{subreddit}/comments/1",
                        }
                    }
                ]
            }
        },
    )


def _comments_response() -> _StubResponse:
    return _StubResponse(
        status=200,
        payload=[
            {},
            {
                "data": {
                    "children": [],
                }
            },
        ],
    )


@pytest.fixture
def stub_session() -> _StubSession:
    return _StubSession(
        [
            _token_response(),
            _posts_response("python"),
        ]
    )


async def test_fetch_subreddit_posts_parses_payload(monkeypatch: pytest.MonkeyPatch, stub_session: _StubSession) -> None:
    client = RedditAPIClient(
        "id",
        "secret",
        "testsuite",
        session=stub_session,
    )

    posts, after = await client.fetch_subreddit_posts("python", limit=10)
    assert len(posts) == 1
    post = posts[0]
    assert post.subreddit == "python"
    assert post.score == 42
    assert after is None
    assert client.access_token == "test-token"
    await client.close()


async def test_fetch_multiple_subreddits_deduplicates_names() -> None:
    session = _StubSession(
        [
            _token_response(),
            _posts_response("python"),
            _posts_response("golang"),
        ]
    )
    client = RedditAPIClient(
        "id",
        "secret",
        "testsuite",
        session=session,
    )

    result = await client.fetch_multiple_subreddits(["python", "python", "golang"])
    assert set(result.keys()) == {"python", "golang"}
    assert all(isinstance(posts[0], RedditPost) for posts in result.values())
    await client.close()


async def test_rate_limiting_waits_for_window(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _StubSession(
        [
            _token_response(),
            _posts_response("python"),
            _posts_response("python"),
            _posts_response("python"),
        ]
    )
    client = RedditAPIClient(
        "id",
        "secret",
        "testsuite",
        rate_limit=2,
        rate_limit_window=5.0,
        session=session,
    )

    class FakeClock:
        def __init__(self) -> None:
            self.value = 0.0
            self.sleeps: List[float] = []

        def monotonic(self) -> float:
            return self.value

        async def sleep(self, duration: float) -> None:
            self.sleeps.append(duration)
            self.value += duration

    clock = FakeClock()
    monkeypatch.setattr(time, "monotonic", clock.monotonic)
    monkeypatch.setattr(asyncio, "sleep", clock.sleep)

    await client.fetch_subreddit_posts("python")
    await client.fetch_subreddit_posts("python")
    await client.fetch_subreddit_posts("python")

    assert clock.sleeps, "rate limiter should trigger a sleep"
    assert clock.value >= 5.0
    await client.close()


async def test_fetch_subreddit_posts_timeout_raises() -> None:
    session = _StubSession(
        [
            _token_response(),
            asyncio.TimeoutError(),
            asyncio.TimeoutError(),
        ]
    )
    client = RedditAPIClient("id", "secret", "testsuite", session=session)

    with pytest.raises(RedditAPIError, match="timed out"):
        await client.fetch_subreddit_posts("python", limit=10)

    await client.close()


async def test_fetch_post_comments_request_error_returns_empty_list() -> None:
    session = _StubSession(
        [
            _token_response(),
            asyncio.TimeoutError(),
            asyncio.TimeoutError(),
        ]
    )
    client = RedditAPIClient("id", "secret", "testsuite", session=session)

    comments = await client.fetch_post_comments("post-1", limit=10)
    assert comments == []

    await client.close()


async def test_reddit_client_accepts_hotpost_supply_contract_kwargs() -> None:
    client = RedditAPIClient(
        "id",
        "secret",
        "testsuite",
        search_timeout=12.0,
        low_quota_remaining_threshold=12,
        low_quota_cooldown_seconds=20.0,
        stop_comment_fetch_below_remaining=18,
        max_consecutive_rate_limit_errors=3,
        session=_StubSession([]),
    )

    assert client.search_timeout == 12.0
    assert client.low_quota_remaining_threshold == 12
    assert client.low_quota_cooldown_seconds == 20.0
    assert client.stop_comment_fetch_below_remaining == 18
    assert client.max_consecutive_rate_limit_errors == 3
    assert client.should_skip_comment_fetch() is False

    client._ratelimit_remaining = 17
    assert client.should_skip_comment_fetch() is True

    await client.close()


async def test_fetch_post_comments_accepts_comment_timeout_override() -> None:
    session = _StubSession([
        _token_response(),
        _comments_response(),
    ])
    client = RedditAPIClient("id", "secret", "testsuite", session=session)

    comments = await client.fetch_post_comments("post-1", limit=10, comment_timeout=15.0)

    assert comments == []
    await client.close()
