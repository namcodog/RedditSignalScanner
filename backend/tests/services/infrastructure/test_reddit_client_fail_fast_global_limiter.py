from __future__ import annotations

import pytest

from app.services.infrastructure.reddit_client import RedditAPIClient, RedditGlobalRateLimitExceeded


@pytest.mark.asyncio
async def test_reddit_client_fail_fast_global_limiter_raises() -> None:
    class DummyLimiter:
        async def acquire(self, *, cost: int = 1) -> int:  # noqa: ARG002
            return 10

    client = RedditAPIClient(
        "cid",
        "secret",
        global_rate_limiter=DummyLimiter(),
        fail_fast_on_global_rate_limit=True,
    )

    with pytest.raises(RedditGlobalRateLimitExceeded) as exc:
        await client._throttle()
    assert exc.value.wait_seconds == 10

