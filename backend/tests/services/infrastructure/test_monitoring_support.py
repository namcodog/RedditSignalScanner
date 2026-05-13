from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.infrastructure.monitoring_support import load_entity_extraction_metrics


class _ScalarResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar(self) -> int:
        return self._value


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(self, stmt, params):
        sql = getattr(stmt, "text", str(stmt))
        self.calls.append(sql)
        if "posts_hot" in sql:
            return _ScalarResult(10)
        return _ScalarResult(4)


class _SessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_load_entity_extraction_metrics_reads_semantic_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    monkeypatch.setattr(
        "app.db.session.SessionFactory",
        lambda: _SessionFactory(session),
    )

    payload = await load_entity_extraction_metrics(
        cutoff=datetime(2026, 3, 1, tzinfo=timezone.utc)
    )

    assert payload["recent_posts"] == 10
    assert payload["recent_entities"] == 4
    assert payload["entity_rate"] == 0.4
    assert len(session.calls) == 2
    assert "semantic_observation" in session.calls[1]
    assert "content_entities" not in session.calls[1]
