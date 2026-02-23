from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityPool
from app.models.tier_audit_log import TierAuditLog
from app.models.tier_suggestion import TierSuggestion
from app.models.posts_storage import PostHot
from app.tasks.tier_intelligence_task import (
    _apply_high_confidence_suggestions,
    _generate_daily_tier_suggestions_impl,
)


@pytest.mark.asyncio
async def test_generate_daily_tier_suggestions_runs_without_error(
    db_session: AsyncSession,
) -> None:
    # 准备一个社区和少量 posts_hot，验证任务可以完整运行
    now = datetime.now(timezone.utc)
    pool = CommunityPool(
        name="r/daily_suggestions",
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

    post = PostHot(
        source="reddit",
        source_post_id=f"daily_1_{uuid.uuid4().hex}",
        created_at=now - timedelta(days=1),
        cached_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=5),
        title="Daily suggestion test post",
        body="body",
        subreddit="daily_suggestions",
        score=10,
        num_comments=3,
    )
    db_session.add(post)
    await db_session.commit()

    summary = await _generate_daily_tier_suggestions_impl()

    assert "total_suggestions" in summary
    # 至少验证任务不会抛异常且返回统计字段
    assert summary["total_suggestions"] >= 0
    assert summary["auto_apply_enabled"] is True


@pytest.mark.asyncio
async def test_apply_high_confidence_suggestions_updates_tier_and_logs(
    db_session: AsyncSession,
) -> None:
    # 准备一个启用自动调级的社区和高置信度建议
    pool = CommunityPool(
        name="r/auto_tier",
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
        auto_tier_enabled=True,
    )
    db_session.add(pool)
    await db_session.commit()

    sugg = TierSuggestion(
        community_name="r/auto_tier",
        current_tier="T3",
        suggested_tier="T2",
        confidence=0.95,
        reasons=["high activity"],
        metrics={"posts_per_day": 10.0},
        priority_score=10,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(sugg)
    await db_session.flush()

    await _apply_high_confidence_suggestions(db_session, [sugg])
    await db_session.commit()

    # 重新加载社区和审计日志
    updated_pool = await db_session.scalar(
        select(CommunityPool).where(CommunityPool.name == "r/auto_tier")
    )
    assert updated_pool is not None
    assert updated_pool.tier == "T2"

    logs = (
        await db_session.execute(
            select(TierAuditLog).where(TierAuditLog.community_name == "r/auto_tier")
        )
    ).scalars().all()
    assert logs, "should create at least one audit log"
    assert logs[0].change_source == "auto"
