from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

import pytest

from app.services.reddit_client import RedditAPIClient


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
    def __init__(self) -> None:
        # First call for token, then 403 for listing
        self._responses = [
            _StubResponse(200, {"access_token": "t", "expires_in": 3600}),
            _StubResponse(403, {}),
        ]
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> _StubResponse:  # type: ignore[override]
        if not self._responses:
            raise RuntimeError("No more stub responses")
        return self._responses.pop(0)

    async def close(self) -> None:
        self.closed = True


async def test_fetch_subreddit_posts_403_treated_as_empty() -> None:
    client = RedditAPIClient("id", "secret", "testsuite", session=_StubSession())
    posts = await client.fetch_subreddit_posts("private_sub", limit=10)
    assert posts == []
    await client.close()

