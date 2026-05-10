from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.task import TaskSummary
from app.services.analysis import sample_guard
from app.services.analysis.analysis_readiness_support import (
    build_data_readiness_snapshot,
    build_insufficient_sample_artifacts,
    run_sample_guard_check,
)
from app.services.analysis.topic_profiles import TopicProfile


@dataclass(slots=True)
class _FakeCommunityRow:
    community_key: str
    community_name: str
    sample_posts: int
    sample_comments: int
    registry_enabled: bool = True
    has_membership: bool = True
    is_approved: bool = True
    has_runtime: bool = True
    crawl_status: str = "active"
    runtime_notes: dict[str, object] | None = None
    backfill_floor: datetime | None = None
    last_crawled_at: datetime | None = None


class _FakeMappingResult:
    def __init__(self, rows: list[_FakeCommunityRow]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, object]]:
        return [asdict(row) for row in self._rows]


class _FakeExecuteResult:
    def __init__(self, rows: list[_FakeCommunityRow]) -> None:
        self._rows = rows

    def mappings(self) -> _FakeMappingResult:
        return _FakeMappingResult(self._rows)


class _FakeSession:
    def __init__(self, rows: list[_FakeCommunityRow]) -> None:
        self._rows = rows

    async def execute(
        self,
        _stmt: object,
        _params: object | None = None,
    ) -> _FakeExecuteResult:
        return _FakeExecuteResult(self._rows)


class _FakeSessionContext:
    def __init__(self, rows: list[_FakeCommunityRow]) -> None:
        self._rows = rows

    async def __aenter__(self) -> _FakeSession:
        return _FakeSession(self._rows)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _make_topic_profile(*, allowed_communities: list[str]) -> TopicProfile:
    return TopicProfile(
        id="paypal_v1",
        topic_name="PayPal",
        product_desc="帮助跨境卖家看清 PayPal 手续费、风控冻结和回款拖延问题",
        vertical="payments",
        mode="market_insight",
        allowed_communities=allowed_communities,
        community_patterns=[],
        required_entities_any=[],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
    )


def _make_task_summary() -> TaskSummary:
    now = datetime(2026, 3, 25, tzinfo=timezone.utc)
    return TaskSummary(
        id="00000000-0000-0000-0000-000000000001",
        user_id=None,
        status="processing",
        product_description="帮助跨境卖家看清 PayPal 手续费、风控冻结和回款拖延问题",
        mode="market_insight",
        audit_level="lab",
        topic_profile_id="paypal_v1",
        membership_level=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
        retry_count=0,
        failure_category=None,
    )


@pytest.mark.asyncio
async def test_run_sample_guard_check_returns_none_without_input() -> None:
    result = await run_sample_guard_check(
        keywords=[],
        product_description="   ",
        lookback_days=30,
        min_sample_size=1500,
        hot_fetcher=None,
        cold_fetcher=None,
        supplementer=None,
    )

    assert result is None


@pytest.mark.asyncio
async def test_run_sample_guard_check_forwards_contract() -> None:
    calls: dict[str, object] = {}

    async def hot_fetcher(*, lookback_days: int, keywords: list[str]) -> list[dict[str, object]]:
        calls["hot"] = {"lookback_days": lookback_days, "keywords": keywords}
        return [{"id": "p1"}]

    async def cold_fetcher(*, lookback_days: int, keywords: list[str]) -> list[dict[str, object]]:
        calls["cold"] = {"lookback_days": lookback_days, "keywords": keywords}
        return []

    async def supplementer(
        *, keywords: list[str], shortfall: int, lookback_days: int
    ) -> list[dict[str, object]]:
        calls["supplement"] = {
            "keywords": keywords,
            "shortfall": shortfall,
            "lookback_days": lookback_days,
        }
        return [{"id": "s1"}]

    result = await run_sample_guard_check(
        keywords=["paypal", "payout"],
        product_description="PayPal payout helper",
        lookback_days=90,
        min_sample_size=3,
        hot_fetcher=hot_fetcher,
        cold_fetcher=cold_fetcher,
        supplementer=supplementer,
    )

    assert result == sample_guard.SampleCheckResult(
        hot_count=1,
        cold_count=0,
        combined_count=2,
        shortfall=2,
        remaining_shortfall=1,
        supplemented=True,
        supplement_posts=[{"id": "s1", "source_type": "search"}],
    )
    assert calls["hot"] == {"lookback_days": 90, "keywords": ["paypal", "payout"]}
    assert calls["cold"] == {"lookback_days": 90, "keywords": ["paypal", "payout"]}
    assert calls["supplement"] == {
        "keywords": ["paypal", "payout"],
        "shortfall": 2,
        "lookback_days": 90,
    }


@pytest.mark.asyncio
async def test_build_data_readiness_snapshot_summarizes_hits_and_missing() -> None:
    profile = _make_topic_profile(allowed_communities=["r/PayPal", "Stripe", ""])
    rows = [
        _FakeCommunityRow(
            community_key="paypal",
            community_name="r/PayPal",
            runtime_notes={"backfill_status": "DONE_12M"},
            sample_posts=23,
            sample_comments=9,
            backfill_floor=datetime.now(timezone.utc) - timedelta(days=365),
            last_crawled_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        )
    ]

    snapshot = await build_data_readiness_snapshot(
        topic_profile=profile,
        session_factory=lambda: _FakeSessionContext(rows),
    )

    assert snapshot["target_communities"] == ["r/paypal", "r/stripe"]
    assert snapshot["communities_total"] == 2
    assert snapshot["communities_found"] == 1
    assert snapshot["missing_communities"] == ["r/stripe"]
    assert snapshot["status_counts"] == {"DONE_12M": 1, "MISSING": 1}
    assert snapshot["sample_posts_total"] == 23
    assert snapshot["sample_comments_total"] == 9
    assert snapshot["coverage_months_min"] >= 12
    assert snapshot["coverage_months_avg"] >= 12.0
    assert snapshot["coverage_months_max"] >= 12
    assert snapshot["communities"][0]["community"] == "r/PayPal"
    assert snapshot["communities"][1]["status"] == "MISSING"


def test_build_insufficient_sample_artifacts_preserves_contract() -> None:
    task = _make_task_summary()
    sample_result = sample_guard.SampleCheckResult(
        hot_count=120,
        cold_count=300,
        combined_count=480,
        shortfall=1020,
        remaining_shortfall=940,
        supplemented=True,
        supplement_posts=[{"id": "p1"}],
    )

    artifacts = build_insufficient_sample_artifacts(
        task=task,
        sample_result=sample_result,
        lookback_days=365,
        min_sample_size=1500,
    )

    assert artifacts.insights == {
        "pain_points": [],
        "competitors": [],
        "opportunities": [],
    }
    assert artifacts.sources["analysis_blocked"] == "insufficient_samples"
    assert artifacts.sources["sample_status"] == {
        "hot_count": 120,
        "cold_count": 300,
        "combined_count": 480,
        "shortfall": 1020,
        "remaining_shortfall": 940,
        "supplemented": True,
        "supplement_posts": [{"id": "p1"}],
        "min_required": 1500,
        "lookback_days": 365,
    }
    assert artifacts.sources["report_tier"] == "C_scouting"
    assert artifacts.action_items == []
    assert artifacts.confidence_score == 0.0
    assert "分析暂停：样本不足" in artifacts.report_html
