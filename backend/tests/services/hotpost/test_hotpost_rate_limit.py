from __future__ import annotations

import os

from app.services.hotpost.service import DEFAULT_RATE_LIMIT, DEFAULT_RATE_WINDOW
from app.services.global_rate_limiter import GlobalRateLimiter


class _FakeRedis:
    pass


def test_hotpost_rate_limit_defaults() -> None:
    assert DEFAULT_RATE_LIMIT == 100
    assert DEFAULT_RATE_WINDOW == 600


def test_hotpost_rate_limit_env_override(monkeypatch) -> None:
    monkeypatch.setenv("HOTPOST_RATE_LIMIT_MAX_REQUESTS", "250")
    monkeypatch.setenv("HOTPOST_RATE_LIMIT_WINDOW_SECONDS", "120")

    class _ProbeLimiter(GlobalRateLimiter):
        def __init__(self, redis, *, limit, window_seconds, namespace, client_id) -> None:
            self.limit = limit
            self.window_seconds = window_seconds
            self.namespace = namespace
            self.client_id = client_id
            self._redis = redis

    limiter = _ProbeLimiter(
        _FakeRedis(),
        limit=int(os.getenv("HOTPOST_RATE_LIMIT_MAX_REQUESTS")),
        window_seconds=int(os.getenv("HOTPOST_RATE_LIMIT_WINDOW_SECONDS")),
        namespace="hotpost:qpm",
        client_id="default",
    )
    assert limiter.limit == 250
    assert limiter.window_seconds == 120
