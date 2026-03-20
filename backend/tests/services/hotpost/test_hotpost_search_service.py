from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.schemas.hotpost import Hotpost, HotpostComment, HotpostSearchRequest
from app.services.hotpost.result_meta import HotpostLLMReportResult, HotpostSummaryResult
from app.services.hotpost.service import HotpostService


class _FakeRedis:
    async def get(self, *_args, **_kwargs):
        return None

    async def set(self, *_args, **_kwargs):
        return None

    async def delete(self, *_args, **_kwargs):
        return None

    async def expire(self, *_args, **_kwargs):
        return None


class _FakeTracker:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def mark_processing(self) -> None:
        return None

    async def mark_completed(self) -> None:
        return None

    async def mark_failed(self) -> None:
        return None

    async def mark_degraded(self, *_args, **_kwargs) -> None:
        return None


@pytest.mark.asyncio
async def test_search_passes_community_distribution_into_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(environment="test", allow_mock_fallback=True)
    service = HotpostService(
        settings=settings,
        db=AsyncMock(),
        redis_client=_FakeRedis(),
    )

    post = Hotpost(
        rank=1,
        id="p1",
        title="Best robot vacuum for apartments",
        body_preview="body",
        score=42,
        num_comments=5,
        heat_score=52,
        rant_score=0.0,
        rant_signals=[],
        subreddit="r/robotvacuums",
        author="user",
        reddit_url="https://reddit.com/p1",
        created_utc=0.0,
        signals=["hidden gem"],
        signal_score=12.0,
        top_comments=[],
    )
    comment = HotpostComment(
        comment_fullname="t1_c1",
        author="commenter",
        body="me too",
        score=3,
        permalink="/r/robotvacuums/comments/p1/_/c1",
    )

    captured_distribution: dict[str, str] | None = None

    async def _fake_collect(*_args, **_kwargs):
        from app.services.hotpost.evidence_collection_workflow import HotpostEvidenceCollectionResult

        return HotpostEvidenceCollectionResult(
            subreddits=["r/robotvacuums"],
            api_calls=2,
            raw_posts=1,
            filtered_posts=1,
            relevance_filtered=0,
            top_posts=[post],
            all_comments=[comment],
            categories=["Home_Lifestyle"],
            sentiment_overview={"positive": 1.0, "neutral": 0.0, "negative": 0.0},
            confidence="low",
            community_distribution={"r/robotvacuums": "100%"},
            pain_points=[],
            opportunities=None,
            rant_intensity=None,
            need_urgency=None,
            me_too_count=1,
            notes=[],
        )

    async def _fake_summary(self, *, query: str, posts, confidence: str, sentiment_overview, community_distribution):
        nonlocal captured_distribution
        captured_distribution = community_distribution
        return HotpostSummaryResult(text="fallback summary", source="fallback", degraded_reason="low_confidence")

    monkeypatch.setattr(
        "app.services.hotpost.service.create_hotpost_query",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.hotpost.service.update_hotpost_query",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.hotpost.service.persist_hotpost_search_side_effects",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.hotpost.service.resolve_hotpost_query",
        AsyncMock(return_value=type("Resolution", (), {
            "search_query": "robot vacuum",
            "keywords": ["robot", "vacuum"],
            "subreddits": ["r/robotvacuums"],
            "source": "rule",
            "degraded_reason": None,
        })()),
    )
    monkeypatch.setattr(
        "app.services.hotpost.service.HotpostQueueTracker",
        _FakeTracker,
    )
    monkeypatch.setattr(
        "app.services.hotpost.service.collect_hotpost_evidence",
        _fake_collect,
    )
    monkeypatch.setattr(
        HotpostService,
        "_maybe_llm_summary",
        _fake_summary,
    )
    monkeypatch.setattr(
        "app.services.hotpost.service.build_hotpost_report_result",
        AsyncMock(return_value=HotpostLLMReportResult(report=None, source="disabled", degraded_reason="missing_api_key")),
    )

    response = await service.search(HotpostSearchRequest(query="robot vacuum", limit=10))

    assert captured_distribution == {"r/robotvacuums": "100%"}
    assert response.community_distribution == {"r/robotvacuums": "100%"}
    assert response.debug_info is not None
    assert response.debug_info.summary_source == "fallback"
