from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.llm.post_label_planner import (
    fetch_incremental_post_candidates,
    fetch_post_top_comments,
)


class _FakeMappingsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_FakeMappingsResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeRowResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeSession:
    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def execute(self, _sql: Any, params: dict[str, Any]) -> Any:
        self.calls.append(params)
        return self._results.pop(0)


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


@pytest.mark.asyncio
async def test_fetch_incremental_post_candidates_dedupes_mid_and_high_rows() -> None:
    session = _FakeSession(
        [
            _FakeMappingsResult(
                [
                    {"id": 101, "source": "reddit", "source_post_id": "p101"},
                    {"id": 102, "source": "reddit", "source_post_id": "p102"},
                ]
            ),
            _FakeMappingsResult(
                [
                    {"id": 102, "source": "reddit", "source_post_id": "p102"},
                    {"id": 103, "source": "reddit", "source_post_id": "p103"},
                ]
            ),
        ]
    )

    rows = await fetch_incremental_post_candidates(
        limit=10,
        lookback_days=30,
        session_factory=lambda: _FakeSessionContext(session),
        low_score_max=0.0,
        high_score_min=7.0,
        high_score_ratio=0.3,
    )

    assert [row["id"] for row in rows] == [101, 102, 103]
    assert session.calls[0]["limit"] == 7
    assert session.calls[1]["limit"] == 3


@pytest.mark.asyncio
async def test_fetch_post_top_comments_returns_bodies_in_score_order() -> None:
    session = _FakeSession(
        [
            _FakeRowResult(
                [
                    SimpleNamespace(body="first"),
                    SimpleNamespace(body=None),
                    SimpleNamespace(body="third"),
                ]
            )
        ]
    )

    comments = await fetch_post_top_comments(
        source="reddit",
        source_post_id="abc123",
        limit=3,
        session_factory=lambda: _FakeSessionContext(session),
    )

    assert comments == ["first", "", "third"]
    assert session.calls[0]["post_id"] == "abc123"
    assert session.calls[0]["limit"] == 3
