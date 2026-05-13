from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.hotpost import HotpostSearchRequest, HotpostSearchResponse
from app.services.hotpost.result_meta import HotpostLLMReportResult, HotpostSummaryResult
from app.services.hotpost.search_workflow import (
    HotpostSearchWorkflowDeps,
    HotpostSearchWorkflowInput,
    run_hotpost_search_workflow,
)


class _FakeRedis:
    def __init__(self, payload: str | None = None) -> None:
        self.payload = payload

    async def get(self, *_args, **_kwargs):
        return self.payload


class _FakeTracker:
    def __init__(self, *_args, **_kwargs) -> None:
        self.processing = 0
        self.completed = 0

    async def mark_processing(self) -> None:
        self.processing += 1

    async def mark_completed(self) -> None:
        self.completed += 1


@pytest.mark.asyncio
async def test_search_workflow_returns_cached_payload() -> None:
    cached_payload = HotpostSearchResponse(
        query_id="cached-id",
        query="robot vacuum",
        mode="trending",
        search_time=datetime.now(timezone.utc),
        from_cache=False,
        status="completed",
        summary="cached summary",
        top_posts=[],
        key_comments=[],
        communities=[],
        related_queries=[],
        evidence_count=0,
        community_distribution={},
        sentiment_overview={"positive": 0.0, "neutral": 1.0, "negative": 0.0},
        confidence="none",
        debug_info={
            "query_source": "rule",
            "response_source": "live",
            "summary_source": "fallback",
            "report_source": "disabled",
            "degraded_reasons": [],
        },
    ).model_dump_json()
    redis_client = _FakeRedis(cached_payload)
    update_hotpost_query = AsyncMock()

    result = await run_hotpost_search_workflow(
        workflow_input=HotpostSearchWorkflowInput(
            request=HotpostSearchRequest(query="robot vacuum", limit=10),
        ),
        deps=HotpostSearchWorkflowDeps(
            redis_client=redis_client,
            resolve_mode=lambda _request: "trending",
            resolve_time_filter=lambda _mode, _request: "month",
            resolve_sort=lambda _mode: "top",
            split_search_queries=lambda query, _max_chars: [query],
            resolve_query=AsyncMock(
                return_value=SimpleNamespace(
                    search_query="robot vacuum",
                    keywords=["robot", "vacuum"],
                    subreddits=["r/robotvacuums"],
                    source="rule",
                    degraded_reason=None,
                )
            ),
            create_hotpost_query=AsyncMock(),
            update_hotpost_query=update_hotpost_query,
            tracker_factory=_FakeTracker,
            collect_evidence=AsyncMock(),
            maybe_llm_summary=AsyncMock(),
            build_report_result=AsyncMock(),
            build_search_response=lambda *_args, **_kwargs: None,
            persist_side_effects=AsyncMock(),
            evidence_deps_factory=lambda: SimpleNamespace(lexicon=None),
            report_deps_factory=lambda: object(),
            persistence_deps_factory=lambda: object(),
        ),
    )

    assert result.response.from_cache is True
    assert result.response.debug_info is not None
    assert result.response.debug_info.response_source == "cache"
    update_hotpost_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_workflow_runs_live_path() -> None:
    redis_client = _FakeRedis()
    create_hotpost_query = AsyncMock()
    persist_side_effects = AsyncMock()
    update_hotpost_query = AsyncMock()
    collect_evidence = AsyncMock(
        return_value=SimpleNamespace(
            top_posts=[],
            all_comments=[],
            notes=[],
            subreddits=["r/robotvacuums"],
            raw_posts=2,
            filtered_posts=1,
            relevance_filtered=1,
            sentiment_overview={"positive": 1.0, "neutral": 0.0, "negative": 0.0},
            confidence="low",
            me_too_count=0,
            pain_points=[],
            opportunities=None,
            rant_intensity=None,
            need_urgency=None,
            categories=[],
            api_calls=2,
            community_distribution={"r/robotvacuums": "100%"},
        )
    )
    summary_result = HotpostSummaryResult(text="summary", source="fallback", degraded_reason="low_confidence")
    report_result = HotpostLLMReportResult(report=None, source="disabled", degraded_reason="missing_api_key")
    fake_response = HotpostSearchResponse(
        query_id=str(uuid.uuid4()),
        query="robot vacuum",
        mode="trending",
        search_time=datetime.now(timezone.utc),
        from_cache=False,
        status="degraded",
        summary="summary",
        top_posts=[],
        key_comments=[],
        communities=["r/robotvacuums"],
        related_queries=[],
        evidence_count=0,
        community_distribution={},
        sentiment_overview={"positive": 1.0, "neutral": 0.0, "negative": 0.0},
        confidence="low",
    )

    result = await run_hotpost_search_workflow(
        workflow_input=HotpostSearchWorkflowInput(
            request=HotpostSearchRequest(query="robot vacuum", limit=10),
            llm_model_name="gpt-test",
        ),
        deps=HotpostSearchWorkflowDeps(
            redis_client=redis_client,
            resolve_mode=lambda _request: "trending",
            resolve_time_filter=lambda _mode, _request: "month",
            resolve_sort=lambda _mode: "top",
            split_search_queries=lambda query, _max_chars: [query],
            resolve_query=AsyncMock(
                return_value=SimpleNamespace(
                    search_query="robot vacuum",
                    keywords=["robot", "vacuum"],
                    subreddits=["r/robotvacuums"],
                    source="rule",
                    degraded_reason=None,
                )
            ),
            create_hotpost_query=create_hotpost_query,
            update_hotpost_query=update_hotpost_query,
            tracker_factory=_FakeTracker,
            collect_evidence=collect_evidence,
            maybe_llm_summary=AsyncMock(return_value=summary_result),
            build_report_result=AsyncMock(return_value=report_result),
            build_search_response=lambda _bundle: fake_response,
            persist_side_effects=persist_side_effects,
            evidence_deps_factory=lambda: SimpleNamespace(lexicon=None),
            report_deps_factory=lambda: object(),
            persistence_deps_factory=lambda: object(),
        ),
    )

    assert result.response.summary == "summary"
    create_hotpost_query.assert_awaited_once()
    persist_side_effects.assert_awaited_once()
    update_hotpost_query.assert_not_awaited()
    collect_evidence.assert_awaited_once()
