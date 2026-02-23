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
from app.services.topic_profiles import TopicProfile


pytestmark = pytest.mark.asyncio


def _profile() -> TopicProfile:
    return TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="面向 Shopify 卖家的广告优化与转化率提升工具",
        vertical="Ecommerce_Business",
        # 这里刻意不放 r/shopify 这类“品牌社区”，避免“subreddit 本身暗含锚点”导致测试用例失真。
        allowed_communities=["r/facebookads", "r/ppc", "r/entrepreneur"],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=["ROAS", "CPC", "campaign"],
        exclude_keywords_any=[],
        mode="operations",
        require_context_for_fetch=True,
        context_keywords_any=["ROAS", "campaign"],
        pain_min_mentions=5,
    )


async def test_run_analysis_blocks_as_insufficient_samples_when_required_anchor_filters_out_all_posts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    monkeypatch.setattr(analysis_engine_module.sample_guard, "check_sample_size", _pass_guard)

    # Ensure topic profile loads.
    monkeypatch.setattr(analysis_engine_module, "load_topic_profiles", lambda: [_profile()])

    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    # When the post set is empty after the "required_entities" anchor filter,
    # we must treat it as insufficient_samples (self-healing), not X_blocked.
    async def fake_backfill(*_: object, **__: object) -> list[dict[str, object]]:
        return [
            {
                "type": "backfill_posts",
                "queue": "backfill_posts_queue_v2",
                "targets": 10,
                "crawl_run_id": "00000000-0000-0000-0000-000000000000",
                "target_ids": ["00000000-0000-0000-0000-000000000001"],
            }
        ]

    monkeypatch.setattr(
        analysis_engine_module,
        "_schedule_auto_backfill_for_insufficient_samples",
        fake_backfill,
    )

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            # Posts mention ROAS but NOT Shopify, so they should be filtered out by required_entities_any.
            posts_by_subreddit: dict[str, list[RedditPost]] = {}
            for idx, subreddit in enumerate(communities[:3]):
                posts_by_subreddit[subreddit] = [
                    RedditPost(
                        id=f"t3_{uuid4().hex[:10]}{idx:02d}",
                        title=f"[{idx}] ROAS dropped again",
                        selftext="Campaign performance is weird; ROAS unstable.",
                        score=50,
                        num_comments=0,
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

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="面向 Shopify 卖家的广告优化与转化率提升工具",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        mode="operations",
        audit_level="gold",
        membership_level="pro",
    )

    result = await run_analysis(task, data_collection=StubService())

    assert result.sources.get("analysis_blocked") == "insufficient_samples"
    assert result.sources.get("report_tier") == "C_scouting"
    actions = result.sources.get("remediation_actions") or []
    assert any(isinstance(a, dict) and a.get("type") == "backfill_posts" for a in actions)
    lineage = result.sources.get("data_lineage")
    assert isinstance(lineage, dict)
    assert isinstance(lineage.get("crawler_run_ids"), list)
    assert isinstance(lineage.get("target_ids"), list)


async def test_run_analysis_proceeds_when_some_posts_exist_but_below_topic_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    monkeypatch.setattr(analysis_engine_module.sample_guard, "check_sample_size", _pass_guard)
    monkeypatch.setattr(analysis_engine_module, "load_topic_profiles", lambda: [_profile()])

    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)

    async def fake_backfill(*_: object, **__: object) -> list[dict[str, object]]:
        return [
            {
                "type": "backfill_posts",
                "queue": "backfill_posts_queue_v2",
                "targets": 10,
                "crawl_run_id": "00000000-0000-0000-0000-000000000000",
                "target_ids": ["00000000-0000-0000-0000-000000000001"],
            }
        ]

    monkeypatch.setattr(
        analysis_engine_module,
        "_schedule_auto_backfill_for_insufficient_samples",
        fake_backfill,
    )

    async def _skip_comment_backfill(*_: object, **__: object) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr(
        analysis_engine_module,
        "_schedule_auto_backfill_for_missing_comments",
        _skip_comment_backfill,
    )

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            posts_by_subreddit: dict[str, list[RedditPost]] = {}
            for idx, subreddit in enumerate(communities[:1]):
                posts_by_subreddit[subreddit] = [
                    RedditPost(
                        id=f"t3_{uuid4().hex[:10]}{idx:02d}{j:02d}",
                        title=f"[{j}] Shopify ROAS dropped - campaign help",
                        selftext=f"Need help with Shopify ads campaign #{j}. ROAS unstable.",
                        score=50 + j,
                        num_comments=0,
                        created_utc=1.0 + j,
                        subreddit=subreddit,
                        author=f"author_{j}",
                        url=f"https://reddit.com/{subreddit}/shopify/roas/{j}",
                        permalink=f"/{subreddit}/shopify/roas/{j}",
                    )
                    for j in range(5)
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

    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="面向 Shopify 卖家的广告优化与转化率提升工具",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        mode="operations",
        audit_level="gold",
        membership_level="pro",
    )

    result = await run_analysis(task, data_collection=StubService())

    # Still treated as warmup/insufficient_samples (Contract B), but the pipeline should proceed
    # with a scouting report instead of an empty "paused" package.
    assert result.sources.get("analysis_blocked") == "insufficient_samples"
    assert int(result.sources.get("posts_analyzed") or 0) > 0
    assert "duplicates_summary" in result.sources
    actions = result.sources.get("remediation_actions") or []
    assert any(isinstance(a, dict) and a.get("type") == "backfill_posts" for a in actions)
