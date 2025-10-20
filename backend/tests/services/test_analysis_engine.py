from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

import pytest

from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services import analysis_engine as analysis_engine_module
from app.services.analysis_engine import run_analysis
from app.services.data_collection import CollectionResult
from app.services.reddit_client import RedditPost
from app.services.analysis.sample_guard import SampleCheckResult


@pytest.fixture(autouse=True)
def _allow_sample_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default sample guard behaviour for tests: always meets the floor."""

    async def _pass_guard(**_: object) -> SampleCheckResult:
        return SampleCheckResult(
            hot_count=900,
            cold_count=700,
            combined_count=1600,
            shortfall=0,
            remaining_shortfall=0,
            supplemented=False,
            supplement_posts=[],
        )

    monkeypatch.setattr(
        analysis_engine_module.sample_guard,
        "check_sample_size",
        _pass_guard,
    )


@pytest.mark.asyncio
async def test_run_analysis_produces_signals_without_external_services() -> None:
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="AI-powered note taking app for researchers needing nightly summaries.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    assert result.sources["analysis_duration_seconds"] < 270
    # 缓存优先架构承诺90%数据来自缓存（PRD-03 §1.4）
    assert result.sources["cache_hit_rate"] >= 0.9
    assert result.sources["reddit_api_calls"] == 0
    assert len(result.insights["pain_points"]) >= 5
    assert result.insights["pain_points"][0]["severity"] in {"high", "medium", "low"}
    assert isinstance(result.insights["pain_points"][0]["user_examples"], list)
    assert len(result.insights["competitors"]) >= 3
    assert result.insights["competitors"][0]["market_share"] >= 0
    assert len(result.insights["opportunities"]) >= 3
    assert "<h1>Reddit Signal Scanner 分析报告</h1>" in result.report_html
    assert isinstance(result.insights["pain_points"][0]["example_posts"], list)
    assert "market_share" in result.insights["competitors"][0]
    assert "key_insights" in result.insights["opportunities"][0]
    assert isinstance(result.sources.get("communities_detail"), list)
    assert result.sources["product_description"]


@pytest.mark.asyncio
async def test_run_analysis_prefers_cache_when_api_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_posts = {
        "r/artificial": [
            RedditPost(
                id="r/artificial-1",
                title="Users can't stand the slow onboarding workflow",
                selftext="I can't stand how painfully slow the onboarding workflow feels for research teams.",
                score=180,
                num_comments=20,
                created_utc=1.0,
                subreddit="r/artificial",
                author="tester",
                url="https://reddit.com/r/artificial/1",
                permalink="/r/artificial/comments/1",
            ),
            RedditPost(
                id="r/artificial-2",
                title="Notion vs Evernote for automation reports",
                selftext="Notion vs Evernote showdown as an alternative to automate reporting flows.",
                score=140,
                num_comments=12,
                created_utc=1.0,
                subreddit="r/artificial",
                author="tester",
                url="https://reddit.com/r/artificial/2",
                permalink="/r/artificial/comments/2",
            ),
            RedditPost(
                id="r/artificial-3",
                title="Looking for an automation tool that would pay for itself",
                selftext="Looking for an automation tool that would pay for itself with weekly insight digests.",
                score=120,
                num_comments=8,
                created_utc=1.0,
                subreddit="r/artificial",
                author="tester",
                url="https://reddit.com/r/artificial/3",
                permalink="/r/artificial/comments/3",
            ),
        ],
        "r/ProductManagement": [
            RedditPost(
                id="r/ProductManagement-1",
                title="Why is export still so confusing for product teams?",
                selftext="Why is export so confusing and unreliable even for product teams working on automation?",
                score=160,
                num_comments=18,
                created_utc=1.0,
                subreddit="r/ProductManagement",
                author="tester",
                url="https://reddit.com/r/ProductManagement/1",
                permalink="/r/ProductManagement/comments/1",
            ),
            RedditPost(
                id="r/ProductManagement-2",
                title="Problem with automation quality in customer reports",
                selftext="Problem with automation quality: the generated reports feel confusing and frustrating for stakeholders.",
                score=150,
                num_comments=14,
                created_utc=1.0,
                subreddit="r/ProductManagement",
                author="tester",
                url="https://reddit.com/r/ProductManagement/2",
                permalink="/r/ProductManagement/comments/2",
            ),
            RedditPost(
                id="r/ProductManagement-3",
                title="Need an automation assistant for exec summaries",
                selftext="Need an automation assistant for exec summaries that keeps leadership updated without manual prep.",
                score=120,
                num_comments=10,
                created_utc=1.0,
                subreddit="r/ProductManagement",
                author="tester",
                url="https://reddit.com/r/ProductManagement/3",
                permalink="/r/ProductManagement/comments/3",
            ),
        ],
        "r/startups": [
            RedditPost(
                id="r/startups-1",
                title="Why is export still so confusing?",
                selftext="Why is export still so confusing and unreliable even after the recent upgrade?",
                score=150,
                num_comments=15,
                created_utc=1.0,
                subreddit="r/startups",
                author="tester",
                url="https://reddit.com/r/startups/1",
                permalink="/r/startups/comments/1",
            ),
            RedditPost(
                id="r/startups-2",
                title="Can't believe onboarding still doesn't work",
                selftext="Can't believe onboarding still doesn't work for enterprise customers; it's frustrating.",
                score=130,
                num_comments=10,
                created_utc=1.0,
                subreddit="r/startups",
                author="tester",
                url="https://reddit.com/r/startups/2",
                permalink="/r/startups/comments/2",
            ),
            RedditPost(
                id="r/startups-3",
                title="Need a simple way to keep leadership updated",
                selftext="Need a simple way to keep leadership updated with weekly automation summaries.",
                score=110,
                num_comments=9,
                created_utc=1.0,
                subreddit="r/startups",
                author="tester",
                url="https://reddit.com/r/startups/3",
                permalink="/r/startups/comments/3",
            ),
            RedditPost(
                id="r/startups-4",
                title="Linear vs Jira as an alternative for feedback workflows",
                selftext="Linear vs Jira compared as an alternative to handle automation and feedback workflows.",
                score=125,
                num_comments=11,
                created_utc=1.0,
                subreddit="r/startups",
                author="tester",
                url="https://reddit.com/r/startups/4",
                permalink="/r/startups/comments/4",
            ),
        ],
    }

    class StubCacheManager:
        def __init__(self, *args, **kwargs) -> None:
            self._data = seed_posts

        def get_cached_posts(self, subreddit: str, *, max_age_hours: int = 24) -> List[RedditPost] | None:
            posts = self._data.get(subreddit)
            if not posts:
                return None
            return list(posts)

    monkeypatch.setattr(analysis_engine_module, "CacheManager", StubCacheManager)

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Automation assistant for startup researchers",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    assert len(result.insights["pain_points"]) >= 5
    assert len(result.insights["competitors"]) >= 3
    assert len(result.insights["opportunities"]) >= 3
    assert result.sources["reddit_api_calls"] == 0
    assert isinstance(result.insights["pain_points"][0]["example_posts"], list)


@pytest.mark.asyncio
async def test_run_analysis_uses_explicit_data_collection_service(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_communities: List[str] = []

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(self, communities: List[str], *, limit_per_subreddit: int = 100) -> CollectionResult:
            captured_communities.extend(communities)
            first = communities[0] if communities else "r/artificial"
            posts = [
                RedditPost(
                    id=f"{first}-123",
                    title="Benchmarking automation latency",
                    selftext="Users report the workflow is painfully slow.",
                    score=210,
                    num_comments=22,
                    created_utc=1.0,
                    subreddit=first,
                    author="tester",
                    url=f"https://reddit.com/{first}/123",
                    permalink=f"/{first}/123",
                )
            ]
            return CollectionResult(
                total_posts=len(posts),
                cache_hits=1,
                api_calls=2,
                cache_hit_rate=1.0,
                posts_by_subreddit={first: posts},
                cached_subreddits={first},
            )

        async def close(self) -> None:  # pragma: no cover - close not used in this branch
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Measure automation latency improvements",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)

    assert captured_communities, "Expected collect_posts to receive community list"
    assert result.sources["reddit_api_calls"] == 2
    assert result.sources["posts_analyzed"] >= 1
    assert isinstance(result.sources.get("communities_detail"), list)


@pytest.mark.asyncio
async def test_run_analysis_closes_temporary_service(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubService:
        def __init__(self) -> None:
            self.closed = False
            self.reddit = self

        async def collect_posts(self, communities: List[str], *, limit_per_subreddit: int = 100) -> CollectionResult:
            posts = [
                RedditPost(
                    id="r/artificial-999",
                    title="Automation assistant delivers opportunities",
                    selftext="Looking for automation opportunities with strong signals.",
                    score=150,
                    num_comments=10,
                    created_utc=1.0,
                    subreddit="r/artificial",
                    author="tester",
                    url="https://reddit.com/r/artificial/999",
                    permalink="/r/artificial/999",
                )
            ]
            return CollectionResult(
                total_posts=len(posts),
                cache_hits=1,
                api_calls=1,
                cache_hit_rate=1.0,
                posts_by_subreddit={"r/artificial": posts},
                cached_subreddits={"r/artificial"},
            )

        async def close(self) -> None:
            self.closed = True

    stub_service = StubService()

    def fake_build_service(settings: object) -> StubService:
        return stub_service

    monkeypatch.setattr(analysis_engine_module, "_build_data_collection_service", fake_build_service)

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Automation assistant for market research",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    assert stub_service.closed, "Expected temporary Reddit client to be closed"
    assert result.sources["reddit_api_calls"] == 1


@pytest.mark.asyncio
async def test_run_analysis_returns_notice_on_sample_shortfall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shortfall_result = SampleCheckResult(
        hot_count=120,
        cold_count=180,
        combined_count=300,
        shortfall=1200,
        remaining_shortfall=400,
        supplemented=True,
        supplement_posts=[
            {
                "id": "search-1",
                "title": "Need automation tooling",
                "source_type": "search",
            }
        ],
    )

    async def _shortfall_guard(**_: object) -> SampleCheckResult:
        return shortfall_result

    monkeypatch.setattr(
        analysis_engine_module.sample_guard,
        "check_sample_size",
        _shortfall_guard,
    )

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Lightweight automation assistant for founders.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    assert result.sources["analysis_blocked"] == "insufficient_samples"
    status = result.sources["sample_status"]
    assert status["combined_count"] == shortfall_result.combined_count
    assert status["remaining_shortfall"] == shortfall_result.remaining_shortfall
    assert status["supplemented"] is True
    assert result.insights["pain_points"] == []
    assert result.insights["competitors"] == []
    assert result.insights["opportunities"] == []
    assert "样本不足" in result.report_html
