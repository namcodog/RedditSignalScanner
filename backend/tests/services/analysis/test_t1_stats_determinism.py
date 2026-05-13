from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.analysis import t1_stats


class _DummyResult:
    def __init__(self, rows: list[object] | None = None) -> None:
        self._rows = rows or []

    def fetchall(self) -> list[object]:
        return self._rows


class _RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def execute(self, stmt, params=None):
        self.calls.append((getattr(stmt, "text", str(stmt)), params or {}))
        return _DummyResult([])


@pytest.mark.asyncio
async def test_build_stats_snapshot_uses_fixed_anchor_timestamp(monkeypatch) -> None:
    fixed = datetime(2026, 3, 12, 3, 0, tzinfo=timezone.utc)

    async def fake_posts_comments(session, *, subs, since_dt, anchor_ts):
        assert since_dt == fixed - timedelta(days=30)
        assert anchor_ts == fixed
        return {"r/test": (3, 4, 1, 2)}

    async def fake_ps_ratio(session, *, subs, since_dt):
        assert since_dt == fixed - timedelta(days=30)
        return {"r/test": (5, 2)}

    async def fake_aspects(session, *, subs, since_dt):
        return []

    async def fake_brand_pain(session, *, subs, since_dt, limit):
        return []

    monkeypatch.setattr(t1_stats, "_fetch_posts_comments", fake_posts_comments)
    monkeypatch.setattr(t1_stats, "_fetch_ps_ratio_by_sub", fake_ps_ratio)
    monkeypatch.setattr(t1_stats, "_fetch_aspect_breakdown", fake_aspects)
    monkeypatch.setattr(t1_stats, "_fetch_brand_pain_cooccurrence", fake_brand_pain)

    snapshot = await t1_stats.build_stats_snapshot(
        _RecordingSession(),
        subreddits=["r/test"],
        days=30,
        anchor_ts=fixed,
    )

    assert snapshot.generated_at == fixed.isoformat()
    assert snapshot.since_utc == (fixed - timedelta(days=30)).isoformat()


@pytest.mark.asyncio
async def test_fetch_topic_relevant_communities_uses_fixed_anchor_timestamp(monkeypatch) -> None:
    fixed = datetime(2026, 3, 12, 3, 0, tzinfo=timezone.utc)
    session = _RecordingSession()
    diagnostics: dict[str, object] = {}

    class _NoEmbedding:
        def encode(self, topic: str) -> list[float]:
            raise RuntimeError("disable embedding for deterministic unit test")

    async def fake_comments_rel(_session):
        return "comments"

    monkeypatch.setattr(t1_stats, "embedding_service", _NoEmbedding())
    monkeypatch.setattr(t1_stats, "get_comments_core_lab_relation", fake_comments_rel)

    result = await t1_stats.fetch_topic_relevant_communities(
        session,
        topic="robot vacuum cleaner",
        topic_tokens=["robot", "vacuum"],
        exclusion_tokens=[],
        days=365,
        anchor_ts=fixed,
        diagnostics=diagnostics,
    )

    assert result == {}
    assert len(session.calls) == 2
    window_starts = {params["window_start"] for _, params in session.calls}
    assert fixed - timedelta(days=365) in window_starts
    assert fixed - timedelta(days=180) in window_starts
    for sql, params in session.calls:
        assert "NOW()" not in sql
        assert params["anchor_ts"] == fixed
        assert params["year_window_start"] == fixed - timedelta(days=365)
    assert diagnostics["semantic_search_status"] == "keyword_only"


@pytest.mark.asyncio
async def test_build_entity_sentiment_matrix_uses_fixed_anchor_timestamp(monkeypatch) -> None:
    fixed = datetime(2026, 3, 12, 3, 0, tzinfo=timezone.utc)
    session = _RecordingSession()

    async def fake_comments_rel(_session):
        return "comments"

    monkeypatch.setattr(t1_stats, "get_comments_core_lab_relation", fake_comments_rel)

    result = await t1_stats.build_entity_sentiment_matrix(
        session,
        topic_tokens=["robot", "vacuum"],
        months=12,
        min_mentions=3,
        anchor_ts=fixed,
    )

    assert result == {}
    assert len(session.calls) == 1
    sql, params = session.calls[0]
    assert "NOW()" not in sql
    assert params["anchor_ts"] == fixed
    assert params["months"] == 12
