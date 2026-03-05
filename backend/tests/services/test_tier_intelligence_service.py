from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis.tier_intelligence import TierIntelligenceService, TierThresholds
from app.models.community_pool import CommunityPool
from app.models.posts_storage import PostRaw


@pytest.mark.asyncio
async def test_calculate_community_metrics_with_no_data(db_session: AsyncSession) -> None:
    service = TierIntelligenceService(db_session)
    metrics = await service.calculate_community_metrics("r/empty", lookback_days=30)

    assert metrics.posts_per_day == 0
    assert metrics.comments_per_day == 0
    assert metrics.pain_density == 0
    assert metrics.brand_mentions == 0


@pytest.mark.asyncio
async def test_calculate_community_metrics_tolerates_legacy_pain_tag_category(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    subreddit = "r/test_pain_tag"

    pool = CommunityPool(
        name=subreddit,
        tier="T3",
        categories={"source": "test"},
        description_keywords={"keywords": ["k1"]},
        daily_posts=0,
        avg_comment_length=0,
        quality_score=0.5,
        priority="medium",
        user_feedback_count=0,
        discovered_count=0,
        is_active=True,
    )
    db_session.add(pool)
    await db_session.flush()

    post = PostRaw(
        source_post_id=f"post_{uuid.uuid4().hex}",
        created_at=now,
        title="Test post",
        body="Test body",
        subreddit=subreddit,
        community_id=pool.id,
        is_current=True,
    )
    db_session.add(post)

    await db_session.flush()

    await db_session.execute(
        text(
            """
            INSERT INTO content_labels (content_type, content_id, category, aspect, created_at)
            VALUES
              ('post', :post_id, 'pain_tag', 'other', :created_at)
            """
        ),
        {"post_id": post.id, "created_at": now},
    )

    service = TierIntelligenceService(db_session)
    try:
        metrics = await service.calculate_community_metrics(subreddit, lookback_days=30)
        assert metrics.pain_density > 0
    finally:
        await db_session.rollback()


@pytest.mark.asyncio
async def test_generate_tier_suggestions_basic_flow(db_session: AsyncSession) -> None:
    # 准备一个社区和一些 posts_hot 数据
    now = datetime.now(timezone.utc)

    pool = CommunityPool(
        name="r/tier_test",
        tier="T3",
        categories={"source": "test"},
        description_keywords={"keywords": ["k1"]},
        daily_posts=0,
        avg_comment_length=0,
        quality_score=0.9,
        priority="medium",
        user_feedback_count=0,
        discovered_count=0,
        is_active=True,
    )
    db_session.add(pool)
    await db_session.flush()

    # 过去 10 天内每隔一天插入一条 post，确保有一定活跃度
    posts: list[PostRaw] = []
    for i in range(10):
        created_at = now - timedelta(days=i)
        post = PostRaw(
            source_post_id=f"post_{i}_{uuid.uuid4().hex}",
            created_at=created_at,
            title=f"Sample post {i}",
            body="example body",
            subreddit="r/tier_test",
            score=10 + i,
            num_comments=5,
            community_id=pool.id,
        )
        posts.append(post)
        db_session.add(post)

    await db_session.commit()

    service = TierIntelligenceService(db_session)

    # 使用宽松的阈值，确保会产生“升级”建议
    thresholds = TierThresholds(
        promote_to_t1=TierThresholds.PromoteToT1(
            min_posts_per_day=0.1,
            min_pain_density=0.0,
            min_semantic_score=0.5,
            min_labeling_coverage=0.0,
            min_growth_rate=0.0,
        ),
        promote_to_t2=TierThresholds.PromoteToT2(
            min_posts_per_day=0.05,
            min_pain_density=0.0,
            min_semantic_score=0.3,
            min_labeling_coverage=0.0,
            min_growth_rate=0.0,
        ),
        demote_to_t3=TierThresholds.DemoteToT3(
            max_posts_per_day=1000.0,
            max_pain_density=1.0,
            min_labeling_coverage=0.0,
            max_growth_rate=10.0,
        ),
        remove_from_pool=TierThresholds.RemoveFromPool(
            max_posts_per_day=0.0,
            max_spam_ratio=1.0,
            min_labeling_coverage=0.0,
        ),
    )

    suggestions = await service.generate_tier_suggestions(thresholds=thresholds)

    # 至少应有一个针对 r/tier_test 的建议
    assert suggestions
    names = {s["community"] for s in suggestions}
    assert "r/tier_test" in names

    entry = next(s for s in suggestions if s["community"] == "r/tier_test")
    assert entry["current_tier"] == "T3"
    # 宽松阈值下，应该推荐升级到 T1 或 T2
    assert entry["suggested_tier"] in {"T1", "T2"}
    assert 0.0 <= entry["confidence"] <= 1.0
    assert isinstance(entry["reasons"], list)
