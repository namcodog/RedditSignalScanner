from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import pytest

from app.services.reddit_client import RedditAPIClient, RedditPost


pytestmark = pytest.mark.asyncio


@dataclass
class _StubResponse:
    status: int
    payload: Dict[str, Any]

    async def __aenter__(self) -> "_StubResponse":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def json(self) -> Dict[str, Any]:
        return self.payload

    async def text(self) -> str:
        return json.dumps(self.payload)


class _StubSession:
    def __init__(self, responses: Sequence[_StubResponse]) -> None:
        self._responses = list(responses)
        self.requests: List[Dict[str, Any]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> _StubResponse:
        if not self._responses:
            raise RedditAPIError(f"Unexpected request: {method} {url}")
        self.requests.append(
            {
                "method": method,
                "url": url,
                "kwargs": kwargs,
            }
        )
        return self._responses.pop(0)

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

    posts = await client.fetch_subreddit_posts("python", limit=10)
    assert len(posts) == 1
    post = posts[0]
    assert post.subreddit == "python"
    assert post.score == 42
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
