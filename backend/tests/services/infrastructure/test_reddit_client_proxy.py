from __future__ import annotations

import types
import sys

import pytest

from app.services.infrastructure.reddit_client import RedditAPIClient


pytestmark = pytest.mark.asyncio


async def test_client_session_uses_trust_env(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, object] = {}

    class _DummySession:
        def __init__(self, *args: object, **kwargs: object) -> None:
            created["kwargs"] = kwargs
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    class _DummyTimeout:
        def __init__(self, total: float | None = None) -> None:
            self.total = total

    dummy = types.SimpleNamespace(ClientSession=_DummySession, ClientTimeout=_DummyTimeout)
    monkeypatch.setitem(sys.modules, "aiohttp", dummy)

    client = RedditAPIClient("id", "secret", "testsuite")
    await client._ensure_session()

    kwargs = created.get("kwargs") or {}
    assert kwargs.get("trust_env") is True
