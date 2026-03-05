from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from app.models.community_pool import CommunityPool
from app.models.posts_storage import PostRaw
from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis import analysis_engine as analysis_engine_module
from app.services.analysis.analysis_engine import run_analysis
from app.services.crawl.data_collection import CollectionResult
from app.services.infrastructure.reddit_client import RedditPost
from app.services.analysis.sample_guard import SampleCheckResult


pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_run_analysis_keeps_source_range_and_aggregates_comment_counts_consistent(
    db_session: "AsyncSession",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    回归：DB 里的 comment.subreddit 可能是小写 r/shopify，但 Reddit API 返回的 post.subreddit
    可能带大小写 r/Shopify。

    如果我们不做社区名归一：
      - source_range.comments > 0
      - aggregates.communities[].comments 全是 0
    会直接触发 range_mismatch → X_blocked（这就是“明明有评论却被硬拦截”的核心原因）。
    """

    async def _noop_record(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(analysis_engine_module, "_record_discovered_communities", _noop_record)
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

    now = datetime.now(timezone.utc)
    pool_name = "r/shopify"
    created_pool = False

    existing = await db_session.execute(
        select(CommunityPool).where(CommunityPool.name == pool_name)
    )
    pool = existing.scalar_one_or_none()
    if pool is None:
        created_pool = True
        pool = CommunityPool(
            name=pool_name,
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
    post_id = f"t3_shopify_case_{nonce}"
    post = PostRaw(
        source="reddit",
        source_post_id=post_id,
        version=1,
        created_at=now,
        title=f"Shopify ROAS help ({post_id})",
        body=f"Need better ROAS and conversion tracking for my Shopify ads. ({post_id})",
        subreddit=pool_name,
        community_id=int(pool.id),
        score=100,
        num_comments=1,
        business_pool="lab",
    )
    db_session.add(post)
    await db_session.flush()

    # comment.subreddit 用小写（真实库里经常是这个形态）
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
            "comment_id": f"t1_{nonce[:18]}_case",
            "source_post_id": post.source_post_id,
            "post_id": int(post.id),
            "subreddit": "r/shopify",
            "body": "Shopify ROAS is killing me. Campaign CTR ok but conversion rate is awful.",
            "created_utc": now,
            "captured_at": now,
        },
    )
    await db_session.commit()

    class StubService:
        def __init__(self) -> None:
            self.reddit = self

        async def collect_posts(
            self, communities: List[str], *, limit_per_subreddit: int = 100
        ) -> CollectionResult:
            # 关键点：post.subreddit 用大小写不同的 r/Shopify，模拟 Reddit 搜索/接口常见写法
            # 同时返回 10 条，确保不会走“窄题 min_posts=10 不足”的 early return。
            posts_by_subreddit: dict[str, list[RedditPost]] = {communities[0]: []}
            ids = [post_id] + [f"t3_{uuid4().hex[:12]}_{i:02d}" for i in range(9)]
            for idx, pid in enumerate(ids):
                posts_by_subreddit[communities[0]].append(
                    RedditPost(
                        id=pid,
                        title=f"[{idx}] Shopify ROAS dropped - campaign help",
                        selftext="Need help with Shopify ads campaign. ROAS unstable.",
                        score=80 - idx,
                        num_comments=1,
                        created_utc=1.0 + idx,
                        subreddit="r/Shopify",
                        author=f"author_{idx}",
                        url=f"https://reddit.com/r/Shopify/{pid}",
                        permalink=f"/r/Shopify/{pid}",
                    )
                )
            cached = set(posts_by_subreddit.keys())
            return CollectionResult(
                total_posts=len(posts_by_subreddit[communities[0]]),
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
        product_description="Optimize Shopify ads conversion funnels with better ROAS.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=now,
        updated_at=now,
    )
    result = await run_analysis(task, data_collection=StubService())

    flags = list((result.sources.get("facts_v2_quality") or {}).get("flags") or [])
    assert "range_mismatch" not in flags

    facts = result.sources.get("facts_v2_package")
    assert isinstance(facts, dict)
    source_range = (facts.get("data_lineage") or {}).get("source_range") or {}
    communities = (facts.get("aggregates") or {}).get("communities") or []
    assert int(source_range.get("comments") or 0) > 0
    assert sum(int(c.get("comments") or 0) for c in communities) == int(
        source_range.get("comments") or 0
    )

    # cleanup
    await db_session.execute(
        text("DELETE FROM comments WHERE source_post_id = :pid"),
        {"pid": post_id},
    )
    await db_session.execute(delete(PostRaw).where(PostRaw.source_post_id == post_id))
    if created_pool:
        await db_session.execute(delete(CommunityPool).where(CommunityPool.id == pool.id))
    await db_session.commit()
