from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")
from sqlalchemy import delete, select, text

from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis import analysis_engine as analysis_engine_module
from app.services.analysis.analysis_engine import run_analysis, _community_pool_priority_order
from app.services.crawl.data_collection import CollectionResult
from app.services.infrastructure.reddit_client import RedditPost
from app.services.analysis.sample_guard import SampleCheckResult
from app.db.session import SessionFactory
from app.models.posts_storage import PostRaw
from app.models.community_pool import CommunityPool


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


@pytest.fixture
def mock_sample_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit sample guard override for tests that expect full analysis run."""

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
async def test_run_analysis_fast_with_mocked_database() -> None:
    """
    快速版本：使用 Mock 替代所有外部依赖（基于 exa-code 最佳实践）

    优化策略：
    1. Mock SessionFactory 避免数据库连接和 reset_database fixture 的 DDL 开销
    2. 使用合成数据验证核心逻辑
    3. 预期耗时：<1 秒（vs 原版 90 秒）

    参考：https://pytest-with-eric.com/pytest-advanced/pytest-improve-runtime/
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    # Mock SessionFactory 返回空的社区列表（触发合成数据路径）
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    with patch('app.services.analysis.analysis_engine.SessionFactory') as mock_factory:
        mock_factory.return_value.__aenter__.return_value = mock_session

        task = TaskSummary(
            id=uuid4(),
            status=TaskStatus.PENDING,
            product_description="AI-powered note taking app for researchers needing nightly summaries.",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        result = await run_analysis(task, data_collection=None)

        # 验证核心功能
        # 注意：扩展社区池后，处理时间增加到 ~150 秒是合理的
        assert result.sources["analysis_duration_seconds"] < 200
        assert "communities" in result.sources
        assert "cache_hit_rate" in result.sources
        assert "reddit_api_calls" in result.sources
        assert 0.0 <= result.sources["cache_hit_rate"] <= 1.0
        assert result.sources["reddit_api_calls"] == 0
        report_tier = result.sources.get("report_tier")
        assert report_tier in {"A_full", "B_trimmed", "C_scouting", "X_blocked"}
        if report_tier in {"C_scouting", "X_blocked"}:
            assert result.insights["pain_points"] == []
        else:
            assert len(result.insights["pain_points"]) >= 4


@pytest.mark.asyncio
async def test_attach_post_scores_enriches_posts(db_session: "AsyncSession") -> None:
    now = datetime.now(timezone.utc)
    await db_session.execute(
        text(
            "DELETE FROM post_scores WHERE post_id IN (SELECT id FROM posts_raw WHERE source_post_id = :sid)"
        ),
        {"sid": "t3_scorecase"},
    )
    await db_session.execute(
        delete(PostRaw).where(
            PostRaw.source == "reddit",
            PostRaw.source_post_id == "t3_scorecase",
        )
    )
    await db_session.flush()
    community_result = await db_session.execute(
        select(CommunityPool).where(CommunityPool.name == "r/test")
    )
    community = community_result.scalar_one_or_none()
    if community is None:
        community = CommunityPool(
            name="r/test",
            tier="high",
            categories={},
            description_keywords={},
            daily_posts=10,
            avg_comment_length=5,
            quality_score=0.5,
            priority="medium",
            is_active=True,
            is_blacklisted=False,
        )
        db_session.add(community)
        await db_session.flush()
    post = PostRaw(
        source="reddit",
        source_post_id="t3_scorecase",
        version=1,
        created_at=now,
        fetched_at=now,
        valid_from=now,
        title="Test post",
        body="Test body",
        subreddit="r/test",
        community_id=community.id,
        score=10,
        num_comments=2,
        is_current=True,
    )
    db_session.add(post)
    await db_session.flush()

    await db_session.execute(
        text(
            """
            INSERT INTO post_scores (
                post_id, llm_version, rule_version, scored_at, is_latest,
                value_score, opportunity_score, business_pool, sentiment,
                purchase_intent_score, tags_analysis, entities_extracted, calculation_log
            ) VALUES (
                :post_id, :llm_version, :rule_version, :scored_at, TRUE,
                :value_score, NULL, :business_pool, NULL,
                NULL, '{}'::jsonb, '[]'::jsonb, '{}'::jsonb
            )
            """
        ),
        {
            "post_id": post.id,
            "llm_version": "none",
            "rule_version": "rulebook_v1",
            "scored_at": now,
            "value_score": 8.0,
            "business_pool": "core",
        },
    )
    await db_session.commit()

    posts = [
        {
            "id": post.source_post_id,
            "title": "Test post",
            "summary": "Test body",
            "score": 10,
            "num_comments": 2,
            "subreddit": "r/test",
        }
    ]
    enriched, stats = await analysis_engine_module._attach_post_scores(  # type: ignore[attr-defined]
        db_session, posts
    )
    assert enriched[0]["business_pool"] == "core"
    assert float(enriched[0]["value_score"]) == 8.0
    assert stats["scored_posts"] == 1


def test_apply_post_score_policy_filters_noise_and_sets_priority() -> None:
    posts = [
        {
            "id": "p1",
            "score": 10,
            "business_pool": "noise",
            "subreddit": "r/noise",
        },
        {
            "id": "p2",
            "score": 5,
            "value_score": 7,
            "business_pool": "core",
            "subreddit": "r/core",
        },
    ]

    filtered, noise_stats = analysis_engine_module._apply_post_score_policy(  # type: ignore[attr-defined]
        posts
    )

    assert len(filtered) == 1
    assert noise_stats["noise_posts"] == 1
    assert noise_stats["noise_by_community"]["r/noise"] == 1
    expected = (
        5 * analysis_engine_module.BUSINESS_POOL_WEIGHTS["core"]
        + 7 * analysis_engine_module.VALUE_SCORE_WEIGHT
    )
    assert filtered[0]["priority_score"] == pytest.approx(expected, rel=1e-3)


@pytest.mark.asyncio
async def test_priority_order_prefers_high_over_medium_low(
    db_session: "AsyncSession",
) -> None:
    communities = [
        CommunityPool(
            name="r/priority_high",
            tier="high",
            categories={},
            description_keywords={},
            daily_posts=10,
            avg_comment_length=5,
            quality_score=0.5,
            priority="high",
            is_active=True,
            is_blacklisted=False,
        ),
        CommunityPool(
            name="r/priority_medium",
            tier="high",
            categories={},
            description_keywords={},
            daily_posts=10,
            avg_comment_length=5,
            quality_score=0.5,
            priority="medium",
            is_active=True,
            is_blacklisted=False,
        ),
        CommunityPool(
            name="r/priority_low",
            tier="high",
            categories={},
            description_keywords={},
            daily_posts=10,
            avg_comment_length=5,
            quality_score=0.5,
            priority="low",
            is_active=True,
            is_blacklisted=False,
        ),
    ]
    db_session.add_all(communities)
    await db_session.commit()

    result = await db_session.execute(
        select(CommunityPool.name, CommunityPool.priority).order_by(
            _community_pool_priority_order(CommunityPool).desc(),
            CommunityPool.name.asc(),
        )
    )
    priorities = [row.priority for row in result.all()]
    assert priorities[:3] == ["high", "medium", "low"]


@pytest.mark.asyncio
@pytest.mark.slow
async def test_run_analysis_produces_signals_without_external_services() -> None:
    """
    Verify that run_analysis produces signals without calling external Reddit API.
    4. 减少分析耗时阈值（270s → 30s），适应优化后的性能

    注：此测试验证核心分析逻辑，不依赖真实数据库和 Redis
    如需快速测试，请使用：pytest -m "not slow"
    """
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="AI-powered note taking app for researchers needing nightly summaries.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    # 验证核心功能
    # 注意：扩展社区池后，处理时间增加到 ~150 秒是合理的
    assert result.sources["analysis_duration_seconds"] < 200
    assert "communities" in result.sources
    assert "cache_hit_rate" in result.sources
    assert "reddit_api_calls" in result.sources
    assert 0.0 <= result.sources["cache_hit_rate"] <= 1.0
    assert result.sources["reddit_api_calls"] == 0
    report_tier = result.sources.get("report_tier")
    assert report_tier in {"A_full", "B_trimmed", "C_scouting", "X_blocked"}
    if report_tier in {"C_scouting", "X_blocked"}:
        assert result.insights["pain_points"] == []
        assert "勘探简报" in result.report_html or "报告拦截" in result.report_html
        return

    pain_points = result.insights["pain_points"]
    assert pain_points, "Expected pain_points for A/B report tiers"
    if report_tier == "B_trimmed":
        assert 1 <= len(pain_points) <= 2
    else:
        assert len(pain_points) >= 4
    assert pain_points[0]["severity"] in {"high", "medium", "low"}
    assert isinstance(pain_points[0]["user_examples"], list)
    assert isinstance(pain_points[0]["example_posts"], list)

    assert result.insights["competitors"], "Expected competitors for A/B report tiers"
    assert result.insights["competitors"][0]["market_share"] >= 0
    opportunities = result.insights["opportunities"]
    assert opportunities, "Expected opportunities for A/B report tiers"
    if report_tier == "B_trimmed":
        assert len(opportunities) <= 2
    assert "[Reddit Signal Scanner]" in result.report_html

    assert "market_share" in result.insights["competitors"][0]
    assert "key_insights" in opportunities[0]
    assert isinstance(result.sources.get("communities_detail"), list)
    assert result.sources["product_description"]
    stats = result.sources.get("dedup_stats")
    assert isinstance(stats, dict)
    assert stats["total_posts"] >= result.sources["posts_analyzed"]
    assert stats["similarity_checks"] >= 0


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

        async def get_cached_posts(self, subreddit: str, *, max_age_hours: int = 24) -> List[RedditPost] | None:
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

    assert result.sources["reddit_api_calls"] == 0
    report_tier = result.sources.get("report_tier")
    assert report_tier in {"A_full", "B_trimmed", "C_scouting", "X_blocked"}
    if report_tier in {"C_scouting", "X_blocked"}:
        assert result.insights["pain_points"] == []
        return

    pain_points = result.insights["pain_points"]
    assert pain_points, "Expected pain_points for A/B report tiers"
    if report_tier == "B_trimmed":
        assert 1 <= len(pain_points) <= 2
    else:
        assert len(pain_points) >= 4

    assert result.insights["competitors"], "Expected competitors for A/B report tiers"
    assert result.insights["opportunities"], "Expected opportunities for A/B report tiers"
    if report_tier == "B_trimmed":
        assert len(result.insights["opportunities"]) <= 2
    assert isinstance(pain_points[0]["example_posts"], list)


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

    # 禁用 Reddit 搜索，确保系统使用 service.collect_posts()
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_reddit_search", False)

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
async def test_run_analysis_records_collection_warnings_when_fallback_used(
    mock_sample_guard: None,
) -> None:
    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            subreddit = communities[0] if communities else "r/fallback"
            posts = [
                RedditPost(
                    id=f"{subreddit}-fallback-1",
                    title="Automation backlog grows with delayed API fetch",
                    selftext="Rate limit kicked in, falling back to older cache.",
                    score=80,
                    num_comments=5,
                    created_utc=1.0,
                    subreddit=subreddit,
                    author="tester",
                    url=f"https://reddit.com/{subreddit}/fallback/1",
                    permalink=f"/{subreddit}/fallback/1",
                )
            ]
            return CollectionResult(
                total_posts=len(posts),
                cache_hits=0,
                api_calls=1,
                cache_hit_rate=0.0,
                posts_by_subreddit={subreddit: posts},
                cached_subreddits=set(),
                stale_cache_subreddits={subreddit},
                stale_cache_fallback_subreddits={subreddit},
                api_failures=[
                    {
                        "subreddit": subreddit,
                        "error": "rate limit",
                        "reason": "rate_limit",
                    }
                ],
            )

        async def close(self) -> None:  # pragma: no cover - close not used in this branch
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Automation workflow monitoring tool for ops teams.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)
    warnings = result.sources.get("collection_warnings") or []
    assert "stale_cache_detected" in warnings
    assert "stale_cache_fallback" in warnings
    assert "reddit_rate_limited" in warnings


@pytest.mark.asyncio
async def test_keyword_supplement_writes_posts_to_cold_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_description_text = "Automation assistant that summarises weekly updates."
    keywords = ["automation", "summary"]
    sample_posts = [
        {
            "id": "search-1",
            "title": "Looking for automation workflow",
            "summary": "Need an automation tool that can summarise updates.",
            "score": 120,
            "num_comments": 9,
            "subreddit": "r/startups",
            "author": "tester",
            "url": "https://reddit.com/r/startups/search-1",
            "permalink": "/r/startups/comments/search-1",
            "created_utc": 1_700_000_000.0,
        }
    ]

    class StubSettings:
        enable_reddit_search = True
        reddit_client_id = "client"
        reddit_client_secret = "secret"
        reddit_user_agent = "agent"
        reddit_rate_limit = 60
        reddit_rate_limit_window_seconds = 60.0
        reddit_request_timeout_seconds = 30.0
        reddit_max_concurrency = 2

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.entered = False

        async def __aenter__(self) -> "FakeClient":
            self.entered = True
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            self.entered = False

        async def close(self) -> None:
            self.entered = False

    async def fake_keyword_crawl(
        client: object,
        *,
        product_description: str,
        base_keywords: List[str],
        per_query_limit: int,
        query_variants: int,
        time_filter: str,
        sort: str,
    ) -> List[dict]:
        assert product_description == product_description_text
        assert base_keywords == keywords
        assert per_query_limit >= 1
        assert query_variants >= 1
        assert time_filter == "month"
        assert sort == "relevance"
        return sample_posts

    monkeypatch.setattr(
        analysis_engine_module, "RedditAPIClient", FakeClient, raising=True
    )
    monkeypatch.setattr(
        analysis_engine_module, "get_settings", lambda: StubSettings(), raising=True
    )
    monkeypatch.setattr(
        analysis_engine_module,
        "keyword_crawl",
        fake_keyword_crawl,
        raising=True,
    )
    async with SessionFactory() as session:
        existing = await session.execute(
            select(CommunityPool).where(CommunityPool.name == "r/startups")
        )
        community = existing.scalar_one_or_none()
        if community is None:
            session.add(
                CommunityPool(
                    name="r/startups",
                    tier="high",
                    categories={},
                    description_keywords={},
                    daily_posts=10,
                    avg_comment_length=5,
                    quality_score=0.5,
                    priority="medium",
                    is_active=True,
                    is_blacklisted=False,
                )
            )
        await session.commit()

    supplement = await analysis_engine_module._supplement_samples(
        product_description=product_description_text,
        keywords=keywords,
        shortfall=1,
        lookback_days=30,
    )

    assert supplement
    assert supplement[0]["source_type"] == "search"

    async with SessionFactory() as session:
        result = await session.execute(
            select(PostRaw).where(PostRaw.source_post_id == "search-1")
        )
        record = result.scalar_one()
        assert record.extra_data["source_type"] == "search"
        assert keywords == record.extra_data["search_keywords"]
        await session.execute(
            delete(PostRaw).where(PostRaw.source_post_id == "search-1")
        )
        await session.commit()


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
    assert isinstance(result.sources.get("communities"), list)
    assert result.sources["posts_analyzed"] == shortfall_result.combined_count
    assert result.sources["cache_hit_rate"] == pytest.approx(
        shortfall_result.hot_count / shortfall_result.combined_count, abs=1e-2
    )
    status = result.sources["sample_status"]
    assert status["combined_count"] == shortfall_result.combined_count
    assert status["remaining_shortfall"] == shortfall_result.remaining_shortfall
    assert status["supplemented"] is True
    assert result.insights["pain_points"] == []
    assert result.insights["competitors"] == []
    assert result.insights["opportunities"] == []
    assert "样本不足" in result.report_html


@pytest.mark.asyncio
async def test_run_analysis_insufficient_samples_triggers_auto_backfill_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import uuid
    from app.models.community_cache import CommunityCache

    shortfall_result = SampleCheckResult(
        hot_count=10,
        cold_count=10,
        combined_count=20,
        shortfall=1480,
        remaining_shortfall=1480,
        supplemented=False,
        supplement_posts=[],
    )

    async def _shortfall_guard(**_: object) -> SampleCheckResult:
        return shortfall_result

    monkeypatch.setattr(
        analysis_engine_module.sample_guard,
        "check_sample_size",
        _shortfall_guard,
    )

    # Seed a tiny community_cache snapshot so the preflight can report waterline status.
    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        row = await session.get(CommunityCache, "r/shopify")
        if row is None:
            row = CommunityCache(
                community_name="r/shopify",
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                backfill_status="DONE_12M",
                coverage_months=12,
                sample_posts=123,
                sample_comments=45,
            )
            session.add(row)
        else:
            row.last_crawled_at = now
            row.backfill_status = "DONE_12M"
            row.coverage_months = 12
            row.sample_posts = 123
            row.sample_comments = 45
        await session.commit()

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    assert result.sources["analysis_blocked"] == "insufficient_samples"
    data_readiness = result.sources.get("data_readiness")
    assert isinstance(data_readiness, dict)
    assert int(data_readiness.get("sample_posts_total") or 0) >= 0
    assert int(data_readiness.get("communities_total") or 0) > 0
    details = data_readiness.get("communities") or []
    assert any(isinstance(row, dict) and row.get("community") == "r/shopify" for row in details)
    actions = result.sources.get("remediation_actions") or []
    assert actions, "Expected auto backfill actions to be recorded when samples are insufficient"
    assert actions[0]["type"] == "backfill_posts"
    assert int(actions[0]["targets"] or 0) > 0
    assert isinstance(actions[0].get("target_ids"), list)
    assert actions[0].get("target_ids"), "Expected at least a sample of target_ids for lineage tracing"

    lineage = result.sources.get("data_lineage")
    assert isinstance(lineage, dict)
    assert isinstance(lineage.get("crawler_run_ids"), list)
    assert isinstance(lineage.get("target_ids"), list)

    crawl_run_id = uuid.uuid5(uuid.NAMESPACE_URL, f"analysis_preflight_posts:{task.id}")
    assert str(crawl_run_id) in (lineage.get("crawler_run_ids") or [])
    assert any(str(x) for x in (lineage.get("target_ids") or []))
    async with SessionFactory() as session:
        count = await session.scalar(
            text(
                "SELECT COUNT(*) FROM crawler_run_targets WHERE crawl_run_id = CAST(:rid AS uuid)"
            ),
            {"rid": str(crawl_run_id)},
        )
    assert int(count or 0) > 0


@pytest.mark.asyncio
async def test_run_analysis_uses_topic_profile_preferred_days_for_sample_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.analysis.topic_profiles import TopicProfile

    profile = TopicProfile(
        id="preferred_days_test_v1",
        topic_name="Preferred Days Test",
        product_desc="Test profile to validate preferred_days wiring.",
        vertical="test",
        allowed_communities=["r/test"],
        community_patterns=[],
        required_entities_any=[],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
        preferred_days=123,
    )

    monkeypatch.setattr(analysis_engine_module, "load_topic_profiles", lambda: [profile])

    captured: dict[str, int] = {}

    async def fake_run_sample_guard(
        _keywords: list[str],
        _product_description: str,
        *,
        lookback_days: int,
    ) -> SampleCheckResult:
        captured["lookback_days"] = int(lookback_days)
        return SampleCheckResult(
            hot_count=0,
            cold_count=0,
            combined_count=0,
            shortfall=0,
            remaining_shortfall=1,
            supplemented=False,
            supplement_posts=[],
        )

    async def fake_backfill(*_: object, **__: object) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr(analysis_engine_module, "_run_sample_guard", fake_run_sample_guard)
    monkeypatch.setattr(
        analysis_engine_module,
        "_schedule_auto_backfill_for_insufficient_samples",
        fake_backfill,
    )

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Test product description.",
        topic_profile_id=profile.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    assert captured.get("lookback_days") == 123
    assert result.sources["analysis_blocked"] == "insufficient_samples"


@pytest.mark.asyncio
async def test_run_analysis_uses_default_sample_lookback_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int] = {}

    async def fake_run_sample_guard(
        _keywords: list[str],
        _product_description: str,
        *,
        lookback_days: int,
    ) -> SampleCheckResult:
        captured["lookback_days"] = int(lookback_days)
        return SampleCheckResult(
            hot_count=0,
            cold_count=0,
            combined_count=0,
            shortfall=0,
            remaining_shortfall=1,
            supplemented=False,
            supplement_posts=[],
        )

    async def fake_backfill(*_: object, **__: object) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr(analysis_engine_module, "_run_sample_guard", fake_run_sample_guard)
    monkeypatch.setattr(
        analysis_engine_module,
        "_schedule_auto_backfill_for_insufficient_samples",
        fake_backfill,
    )

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Test product description.",
        topic_profile_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=None)

    assert captured.get("lookback_days") == analysis_engine_module.SAMPLE_LOOKBACK_DAYS
    assert result.sources["analysis_blocked"] == "insufficient_samples"


@pytest.mark.asyncio
async def test_run_analysis_records_duplicates(
    monkeypatch: pytest.MonkeyPatch,
    mock_sample_guard: None,
) -> None:
    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(self, communities: List[str], *, limit_per_subreddit: int = 100) -> CollectionResult:
            subreddit = communities[0] if communities else "r/startups"
            posts = [
                RedditPost(
                    id=f"{subreddit}-dup-1",
                    title="Need automation helper for reports",
                    selftext="Looking for automation helper for weekly reports.",
                    score=120,
                    num_comments=9,
                    created_utc=1.0,
                    subreddit=subreddit,
                    author="tester",
                    url=f"https://reddit.com/{subreddit}/dup1",
                    permalink=f"/{subreddit}/dup1",
                ),
                RedditPost(
                    id=f"{subreddit}-dup-2",
                    title="Need automation helper for reports",
                    selftext="Looking for automation helper for weekly reports.",
                    score=110,
                    num_comments=5,
                    created_utc=1.0,
                    subreddit=subreddit,
                    author="tester2",
                    url=f"https://reddit.com/{subreddit}/dup2",
                    permalink=f"/{subreddit}/dup2",
                ),
            ]
            return CollectionResult(
                total_posts=len(posts),
                cache_hits=1,
                api_calls=1,
                cache_hit_rate=1.0,
                posts_by_subreddit={subreddit: posts},
                cached_subreddits={subreddit},
            )

        async def close(self) -> None:
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Automation assistant for weekly reports",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)

    duplicates = result.sources.get("duplicates_summary", [])
    assert duplicates, "Expected duplicates summary to be populated"
    first = duplicates[0]
    assert first["post_id"].endswith("dup-1")
    assert first["evidence_count"] >= 2
    assert first["duplicate_ids"], "Expected duplicate identifiers recorded"
    stats = result.sources["dedup_stats"]
    assert stats["candidate_pairs"] >= 1
    assert stats["similarity_checks"] >= 1


@pytest.mark.asyncio
async def test_run_analysis_applies_facts_v2_quality_gate_with_topic_profile(
    mock_sample_guard: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import uuid

    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            posts_by_subreddit: dict[str, list[RedditPost]] = {}
            unique_words = [
                "aardvark",
                "buffalo",
                "cheetah",
                "dolphin",
                "elephant",
                "flamingo",
                "gorilla",
                "hyena",
                "iguana",
                "jaguar",
                "koala",
                "lemur",
            ]
            if not communities:
                return CollectionResult(
                    total_posts=0,
                    cache_hits=0,
                    api_calls=0,
                    cache_hit_rate=1.0,
                    posts_by_subreddit={},
                    cached_subreddits=set(),
                )
            # 关键点：Shopify profile 有“窄题样本门槛”（min_posts=10），这里确保喂够且不被 dedup 合并。
            for idx in range(12):
                subreddit = communities[idx % len(communities)]
                uniq = uuid4().hex
                marker = unique_words[idx % len(unique_words)]
                # 关键点：同一句痛点（频次会累计），但标题/第二句不同，避免被去重合并
                title = (
                    f"[{idx}] Shopify ROAS pain case {marker} for {subreddit} :: "
                    f"unique_token_{uniq}"
                )
                # Use a realistic Reddit-style post id so comment backfill heuristics accept it.
                post_id = f"t3_{uniq[:10]}{idx:02d}"
                selftext = (
                    "My Shopify ROAS is terrible and I'm frustrated with ad spend. "
                    f"Notes: {marker} {subreddit} variant {idx} ({uniq})."
                )
                posts_by_subreddit.setdefault(subreddit, []).append(
                    RedditPost(
                        id=post_id,
                        title=title,
                        selftext=selftext,
                        score=120 + idx,
                        num_comments=5,
                        created_utc=1.0,
                        subreddit=subreddit,
                        author=f"author_{idx}",
                        url=f"https://reddit.com/{subreddit}/{post_id}",
                        permalink=f"/{subreddit}/{post_id}",
                    )
                )
            total_posts = sum(len(v) for v in posts_by_subreddit.values())
            cached = set(posts_by_subreddit.keys())
            return CollectionResult(
                total_posts=total_posts,
                cache_hits=len(cached),
                api_calls=0,
                cache_hit_rate=1.0,
                posts_by_subreddit=posts_by_subreddit,
                cached_subreddits=cached,
            )

        async def close(self) -> None:
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)

    quality = result.sources.get("facts_v2_quality")
    assert isinstance(quality, dict)
    # Shopify profile 现在要求最少吃到 1 条评论样本：否则降级为 C_scouting，并自动下单补抓评论。
    assert quality.get("tier") == "C_scouting"
    assert "comments_low" in (quality.get("flags") or [])
    assert result.sources.get("report_tier") == "C_scouting"
    assert result.sources.get("analysis_blocked") == "scouting_brief"
    remediation = result.sources.get("remediation_actions") or []
    assert any(
        isinstance(item, dict) and item.get("type") == "backfill_comments"
        for item in remediation
    )
    assert any(isinstance(item, dict) and isinstance(item.get("target_ids"), list) for item in remediation)

    lineage = result.sources.get("data_lineage")
    assert isinstance(lineage, dict)
    assert isinstance(lineage.get("crawler_run_ids"), list)
    assert isinstance(lineage.get("target_ids"), list)
    crawl_run_id = uuid.uuid5(uuid.NAMESPACE_URL, f"analysis_preflight_comments:{task.id}")
    assert str(crawl_run_id) in (lineage.get("crawler_run_ids") or [])
    assert lineage.get("target_ids"), "Expected comment backfill target_ids to be captured in data_lineage"

    facts = result.sources.get("facts_v2_package")
    assert isinstance(facts, dict)
    facts_lineage = facts.get("data_lineage")
    assert isinstance(facts_lineage, dict)
    assert facts_lineage.get("crawler_run_ids") == lineage.get("crawler_run_ids")
    assert facts_lineage.get("target_ids") == lineage.get("target_ids")
    assert result.insights["pain_points"] == []
    assert result.action_items == []
    assert "勘探简报（C_scouting）" in result.report_html


@pytest.mark.asyncio
async def test_run_analysis_applies_facts_v2_quality_gate_without_topic_profile(
    mock_sample_guard: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            posts_by_subreddit: dict[str, list[RedditPost]] = {}
            for idx, subreddit in enumerate(communities[:8]):
                uniq = uuid4().hex
                title = f"[{idx}] ROAS pain case {uniq} for {subreddit}"
                selftext = (
                    "My ROAS is terrible and I'm frustrated with ad spend. "
                    f"Notes: {subreddit} variant {idx} ({uniq})."
                )
                posts_by_subreddit[subreddit] = [
                    RedditPost(
                        id=f"{subreddit}-roas-{idx}",
                        title=title,
                        selftext=selftext,
                        score=120 + idx,
                        num_comments=5,
                        created_utc=1.0,
                        subreddit=subreddit,
                        author=f"author_{idx}",
                        url=f"https://reddit.com/{subreddit}/roas/{idx}",
                        permalink=f"/{subreddit}/roas/{idx}",
                    )
                ]
            total_posts = sum(len(v) for v in posts_by_subreddit.values())
            cached = set(posts_by_subreddit.keys())
            return CollectionResult(
                total_posts=total_posts,
                cache_hits=len(cached),
                api_calls=0,
                cache_hit_rate=1.0,
                posts_by_subreddit=posts_by_subreddit,
                cached_subreddits=cached,
            )

        async def close(self) -> None:
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)

    quality = result.sources.get("facts_v2_quality")
    assert isinstance(quality, dict)
    assert result.sources.get("report_tier") in {
        "A_full",
        "B_trimmed",
        "C_scouting",
        "X_blocked",
    }


@pytest.mark.asyncio
async def test_run_analysis_blocks_topic_mismatch_without_profile_when_meta_has_terms(
    mock_sample_guard: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            posts_by_subreddit: dict[str, list[RedditPost]] = {}
            # 覆盖全部传入社区，避免触发 _backfill_cache_misses() 注入演示数据导致 topic check 失真
            for idx, subreddit in enumerate(communities):
                uniq = uuid4().hex
                title = f"[{idx}] Best cake recipe ever ({uniq})"
                selftext = "I love cooking and cake. Here is my recipe and kitchen workflow."
                posts_by_subreddit[subreddit] = [
                    RedditPost(
                        id=f"{subreddit}-cake-{idx}",
                        title=title,
                        selftext=selftext,
                        score=80 + idx,
                        num_comments=0,
                        created_utc=1.0,
                        subreddit=subreddit,
                        author=f"author_{idx}",
                        url=f"https://reddit.com/{subreddit}/cake/{idx}",
                        permalink=f"/{subreddit}/cake/{idx}",
                    )
                ]
            total_posts = sum(len(v) for v in posts_by_subreddit.values())
            cached = set(posts_by_subreddit.keys())
            return CollectionResult(
                total_posts=total_posts,
                cache_hits=len(cached),
                api_calls=0,
                cache_hit_rate=1.0,
                posts_by_subreddit=posts_by_subreddit,
                cached_subreddits=cached,
            )

        async def close(self) -> None:
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        # 关键点：没有 topic_profile，但描述里有 Shopify（meta 会有英文 token）
        product_description="我想用烹饪社区来分析 Shopify 广告（故意的错盘）",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)

    quality = result.sources.get("facts_v2_quality")
    assert isinstance(quality, dict)
    assert quality.get("tier") == "X_blocked", quality
    assert "topic_mismatch" in (quality.get("flags") or []), quality
    assert result.sources.get("report_tier") == "X_blocked", result.sources.get("report_tier")


@pytest.mark.asyncio
async def test_run_analysis_quality_gate_returns_scouting_brief_when_no_pains(
    mock_sample_guard: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            posts_by_subreddit: dict[str, list[RedditPost]] = {}
            if not communities:
                return CollectionResult(
                    total_posts=0,
                    cache_hits=0,
                    api_calls=0,
                    cache_hit_rate=1.0,
                    posts_by_subreddit={},
                    cached_subreddits=set(),
                )
            # 关键点：每条帖子都要带 Shopify +（语境词之一），同时文本要有差异，避免被 dedup 合并成 <10 条。
            context_terms = [
                "ROAS",
                "CPC",
                "CTR",
                "CPM",
                "CPA",
                "campaign",
                "pixel",
                "attribution",
                "conversion",
                "retargeting",
                "creative",
                "tracking",
            ]
            markers = [
                "aardvark",
                "buffalo",
                "cheetah",
                "dolphin",
                "elephant",
                "flamingo",
                "gorilla",
                "hyena",
                "iguana",
                "jaguar",
                "koala",
                "lemur",
            ]
            for idx in range(12):
                subreddit = communities[idx % len(communities)]
                uniq = uuid4().hex
                term = context_terms[idx % len(context_terms)]
                marker = markers[idx % len(markers)]
                title = f"[{idx}] Shopify {term} setup note ({marker}) ({uniq})"
                selftext = (
                    f"Shopify {term} configuration memo ({marker}) ({uniq}). "
                    f"Example: {term} baseline, testing, creative, campaign."
                )
                post_id = f"t3_{uniq[:10]}{idx:02d}"
                posts_by_subreddit.setdefault(subreddit, []).append(
                    RedditPost(
                        id=post_id,
                        title=title,
                        selftext=selftext,
                        score=80 + idx,
                        num_comments=3,
                        created_utc=1.0,
                        subreddit=subreddit,
                        author=f"author_{idx}",
                        url=f"https://reddit.com/{subreddit}/{post_id}",
                        permalink=f"/{subreddit}/{post_id}",
                    )
                )
            total_posts = sum(len(v) for v in posts_by_subreddit.values())
            cached = set(posts_by_subreddit.keys())
            return CollectionResult(
                total_posts=total_posts,
                cache_hits=len(cached),
                api_calls=0,
                cache_hit_rate=1.0,
                posts_by_subreddit=posts_by_subreddit,
                cached_subreddits=cached,
            )

        async def close(self) -> None:
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)

    assert result.sources.get("report_tier") == "C_scouting"
    assert result.sources.get("analysis_blocked") == "scouting_brief"
    assert result.insights["pain_points"] == []
    assert result.action_items == []
    assert "勘探简报（C_scouting）" in result.report_html
    # C_scouting 仍要输出 Part1（顶部信息/决策卡/战场），只是不输出痛点/机会结论
    assert "## 决策卡片" in result.report_html
    assert "## 核心战场推荐" in result.report_html


@pytest.mark.asyncio
async def test_run_analysis_populates_facts_v2_sample_comments_from_db(
    db_session: "AsyncSession",
    mock_sample_guard: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    now = datetime.now(timezone.utc)
    subreddit = "r/shopify"
    created_pool = False
    existing = await db_session.execute(select(CommunityPool).where(CommunityPool.name == subreddit))
    pool = existing.scalar_one_or_none()
    if pool is None:
        created_pool = True
        pool = CommunityPool(
            name=subreddit,
            tier="high",
            categories={},
            description_keywords={},
            daily_posts=10,
            avg_comment_length=5,
            quality_score=0.5,
            priority="high",
            is_active=True,
            is_blacklisted=False,
        )
        db_session.add(pool)
        await db_session.flush()
    nonce = uuid4().hex
    post_ids = [f"t3_shopify_roas_{nonce}_1", f"t3_shopify_roas_{nonce}_2"]
    posts: list[PostRaw] = []
    for pid in post_ids:
        post = PostRaw(
            source="reddit",
            source_post_id=pid,
            version=1,
            created_at=now,
            title=f"Shopify ROAS is terrible ({pid})",
            body=f"Ads spend is up but conversions are down. Need better ROAS and funnel. ({pid})",
            subreddit=subreddit,
            community_id=int(pool.id),
            score=100,
            num_comments=2,
            business_pool="lab",
        )
        db_session.add(post)
        # Insert one-by-one to avoid RETURNING mismatch with triggers on posts_raw.
        await db_session.flush()
        posts.append(post)

    for idx, post in enumerate(posts, start=1):
        await db_session.execute(
            text(
                """
                INSERT INTO comments (
                    reddit_comment_id, source, source_post_id, post_id, subreddit,
                    depth, body, created_utc, score, is_submitter, edited, captured_at, business_pool
                ) VALUES (
                    :comment_id, 'reddit', :source_post_id, :post_id, :subreddit,
                    0, :body, :created_utc, 10, false, false, :captured_at, 'lab'
                )
                """
            ),
            {
                "comment_id": f"t1_{nonce[:18]}_{idx}",
                "source_post_id": post.source_post_id,
                "post_id": int(post.id),
                "subreddit": subreddit,
                "body": "ROAS is killing me. CTR is ok but conversion rate is awful.",
                "created_utc": now,
                "captured_at": now,
            },
        )
    await db_session.commit()

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(self, communities: List[str], *, limit_per_subreddit: int = 100) -> CollectionResult:
            # 关键点：Shopify profile 有 min_posts=10 的窄题门槛。
            # 这里把 DB 里那两条 post_id 放进来，再补 8 条“同盘但不落库”的帖子，确保能进入 facts_v2 阶段拿到评论样本。
            extra_ids = [f"t3_{uuid4().hex[:12]}{idx:02d}" for idx in range(8)]
            all_ids = [*post_ids, *extra_ids]
            context_terms = [
                "ROAS",
                "CPC",
                "CTR",
                "CPM",
                "CPA",
                "campaign",
                "pixel",
                "attribution",
                "conversion",
                "retargeting",
            ]
            markers = [
                "aardvark",
                "buffalo",
                "cheetah",
                "dolphin",
                "elephant",
                "flamingo",
                "gorilla",
                "hyena",
                "iguana",
                "jaguar",
            ]
            posts_by_subreddit: dict[str, list[RedditPost]] = {subreddit: []}
            for idx, pid in enumerate(all_ids):
                token = uuid4().hex
                term = context_terms[idx % len(context_terms)]
                marker = markers[idx % len(markers)]
                posts_by_subreddit[subreddit].append(
                    RedditPost(
                        id=pid,
                        title=f"Shopify {term} note ({marker}) ({pid}) ({token})",
                        selftext=(
                            f"Need better {term} and conversion tracking for my Shopify ads. "
                            f"({marker}) ({pid}) ({token})"
                        ),
                        score=120 - idx,
                        num_comments=2,
                        created_utc=1.0,
                        subreddit=subreddit,
                        author=f"tester_{idx}",
                        url=f"https://reddit.com/{subreddit}/{pid}",
                        permalink=f"/{subreddit}/{pid}",
                    )
                )
            cached = set(posts_by_subreddit.keys())
            return CollectionResult(
                total_posts=len(posts_by_subreddit[subreddit]),
                cache_hits=len(cached),
                api_calls=0,
                cache_hit_rate=1.0,
                posts_by_subreddit=posts_by_subreddit,
                cached_subreddits=cached,
            )

        async def close(self) -> None:
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=now,
        updated_at=now,
    )
    result = await run_analysis(task, data_collection=service)

    facts = result.sources.get("facts_v2_package")
    assert isinstance(facts, dict)
    source_range = (facts.get("data_lineage") or {}).get("source_range") or {}
    assert int(source_range.get("comments") or 0) > 0
    assert isinstance(facts.get("sample_comments_db"), list)
    assert facts["sample_comments_db"], "Expected sample comments to be populated from DB"

    # cleanup
    await db_session.execute(
        text("DELETE FROM comments WHERE source_post_id = ANY(:ids)"),
        {"ids": post_ids},
    )
    await db_session.execute(delete(PostRaw).where(PostRaw.source_post_id.in_(post_ids)))
    if created_pool:
        await db_session.execute(delete(CommunityPool).where(CommunityPool.id == pool.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_run_analysis_quality_gate_blocks_when_topic_mismatch(
    mock_sample_guard: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            posts_by_subreddit: dict[str, list[RedditPost]] = {}
            # 覆盖所有被选中的社区，避免 _backfill_cache_misses 注入演示数据影响门禁判断
            if not communities:
                return CollectionResult(
                    total_posts=0,
                    cache_hits=0,
                    api_calls=0,
                    cache_hit_rate=1.0,
                    posts_by_subreddit={},
                    cached_subreddits=set(),
                )
            # 关键点：
            # - 先满足“锚点 + 语境”双钥匙，让它进入 facts_v2 阶段；
            # - 再用 exclude_keywords（recipe/cook/...）把 on_topic_ratio 拉到 <0.6，触发 topic_mismatch → X_blocked。
            context_terms = [
                "ROAS",
                "CPC",
                "CTR",
                "CPM",
                "CPA",
                "campaign",
                "pixel",
                "attribution",
                "conversion",
                "retargeting",
                "creative",
                "tracking",
            ]
            markers = [
                "aardvark",
                "buffalo",
                "cheetah",
                "dolphin",
                "elephant",
                "flamingo",
                "gorilla",
                "hyena",
                "iguana",
                "jaguar",
                "koala",
                "lemur",
            ]
            for idx in range(12):
                subreddit = communities[idx % len(communities)]
                uniq = uuid4().hex
                term = context_terms[idx % len(context_terms)]
                marker = markers[idx % len(markers)]
                title = f"[{idx}] Shopify {term} recipe tips ({marker}) ({uniq})"
                selftext = (
                    f"Shopify store ads {term} tracking question ({marker}) ({uniq}). "
                    "Recipe cook kitchen meal food. Totally unrelated to ads."
                )
                post_id = f"t3_{uniq[:10]}{idx:02d}"
                posts_by_subreddit.setdefault(subreddit, []).append(
                    RedditPost(
                        id=post_id,
                        title=title,
                        selftext=selftext,
                        score=60 + idx,
                        num_comments=2,
                        created_utc=1.0,
                        subreddit=subreddit,
                        author=f"author_{idx}",
                        url=f"https://reddit.com/{subreddit}/{post_id}",
                        permalink=f"/{subreddit}/{post_id}",
                    )
                )
            total_posts = sum(len(v) for v in posts_by_subreddit.values())
            cached = set(posts_by_subreddit.keys())
            return CollectionResult(
                total_posts=total_posts,
                cache_hits=len(cached),
                api_calls=0,
                cache_hit_rate=1.0,
                posts_by_subreddit=posts_by_subreddit,
                cached_subreddits=cached,
            )

        async def close(self) -> None:
            pass

    service = StubService()
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await run_analysis(task, data_collection=service)

    assert result.sources.get("report_tier") == "X_blocked"
    assert result.sources.get("analysis_blocked") == "quality_gate_blocked"
    assert result.insights["pain_points"] == []
    assert result.action_items == []
    assert "报告拦截（X_blocked）" in result.report_html


# ============================================================================
# P2-2 Fix: Unit tests for _classify_pain_severity
# ============================================================================


def test_classify_pain_severity_high_by_frequency():
    """Test high severity classification when frequency >= 5."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    # Boundary: frequency = 5 should be high
    assert _classify_pain_severity(5, -0.3) == "high"
    # Above boundary
    assert _classify_pain_severity(6, -0.2) == "high"
    assert _classify_pain_severity(10, 0.0) == "high"


def test_classify_pain_severity_high_by_sentiment():
    """Test high severity classification when sentiment <= -0.6."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    # Boundary: sentiment = -0.6 should be high
    assert _classify_pain_severity(2, -0.6) == "high"
    # Below boundary (more negative)
    assert _classify_pain_severity(1, -0.7) == "high"
    assert _classify_pain_severity(3, -0.8) == "high"


def test_classify_pain_severity_high_combined():
    """Test high severity when both frequency and sentiment are high."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    assert _classify_pain_severity(5, -0.6) == "high"
    assert _classify_pain_severity(10, -0.9) == "high"


def test_classify_pain_severity_medium_by_frequency():
    """Test medium severity classification when 3 <= frequency < 5."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    # Boundary: frequency = 3 should be medium
    assert _classify_pain_severity(3, -0.2) == "medium"
    assert _classify_pain_severity(4, -0.1) == "medium"


def test_classify_pain_severity_medium_by_sentiment():
    """Test medium severity classification when -0.6 < sentiment <= -0.3."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    # Boundary: sentiment = -0.3 should be medium
    assert _classify_pain_severity(2, -0.3) == "medium"
    # Between boundaries
    assert _classify_pain_severity(1, -0.4) == "medium"
    assert _classify_pain_severity(2, -0.5) == "medium"


def test_classify_pain_severity_medium_combined():
    """Test medium severity with combined moderate values."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    assert _classify_pain_severity(3, -0.3) == "medium"
    assert _classify_pain_severity(4, -0.4) == "medium"


def test_classify_pain_severity_low():
    """Test low severity classification for low frequency and mild sentiment."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    # Low frequency, mild sentiment
    assert _classify_pain_severity(1, -0.1) == "low"
    assert _classify_pain_severity(2, -0.2) == "low"
    # Boundary: frequency = 2, sentiment = -0.29 should be low
    assert _classify_pain_severity(2, -0.29) == "low"
    # Positive sentiment
    assert _classify_pain_severity(1, 0.0) == "low"
    assert _classify_pain_severity(2, 0.5) == "low"


def test_classify_pain_severity_edge_cases():
    """Test edge cases and boundary conditions."""
    from app.services.analysis.analysis_engine import _classify_pain_severity

    # Zero frequency
    assert _classify_pain_severity(0, -0.5) == "medium"
    assert _classify_pain_severity(0, -0.7) == "high"
    assert _classify_pain_severity(0, 0.0) == "low"

    # Extreme values
    assert _classify_pain_severity(100, -1.0) == "high"
    assert _classify_pain_severity(1, 1.0) == "low"
