from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.utils.subreddit import subreddit_key


def _classify(f_value: float, e_value: float) -> str:
    if f_value >= 5.0:
        return "high_traffic"
    if e_value >= 50 and f_value < 2.0:
        return "hidden_gem"
    if e_value >= 20:
        return "solid_gold"
    return "growing"


def _frequency_for(archetype: str) -> int:
    # 调度频率（小时）
    mapping = {
        "high_traffic": 2,
        "hidden_gem": 4,
        "solid_gold": 6,
        "growing": 12,
    }
    return mapping.get(archetype, 12)


def _priority_for(archetype: str) -> int:
    mapping = {
        "high_traffic": 10,
        "hidden_gem": 20,
        "solid_gold": 30,
        "growing": 50,
    }
    return mapping.get(archetype, 50)


async def recalibrate_crawl_frequencies(db: AsyncSession) -> Dict[str, Any]:
    """
    基于 R-F-E 指标动态调整 community_cache 的抓取频率。
    返回更新统计。
    """
    sql = text(
        """
        SELECT
            subreddit,
            COUNT(*) AS total_posts,
            SUM(score + num_comments) AS total_interactions,
            AVG(score + num_comments) AS avg_engagement,
            MAX(score + num_comments) AS max_engagement
        FROM posts_raw
        WHERE
            is_current = TRUE
            AND is_deleted = FALSE
            AND created_at >= NOW() - INTERVAL '90 days'
        GROUP BY subreddit;
        """
    )

    result = await db.execute(sql)
    rows = result.mappings().all()
    if not rows:
        return {"status": "no_data", "updated": 0}

    updated = 0
    for row in rows:
        total_posts = float(row.get("total_posts") or 0)
        avg_engagement = float(row.get("avg_engagement") or 0.0)

        f_value = round(total_posts / 90.0, 1)
        e_value = round(avg_engagement, 1)
        archetype = _classify(f_value, e_value)
        freq_hours = _frequency_for(archetype)
        priority = _priority_for(archetype)
        norm_sub = subreddit_key(row.get("subreddit") or "")

        stmt = (
            pg_insert(CommunityCache)
            .values(
                community_name=norm_sub,
                last_crawled_at=datetime.now(timezone.utc),
                posts_cached=int(total_posts),
                crawl_priority=priority,
                crawl_frequency_hours=freq_hours,
                ttl_seconds=3600,
                quality_score=0.50,
                hit_count=0,
                last_seen_created_at=None,
                total_posts_fetched=int(total_posts),
                dedup_rate=0,
                avg_valid_posts=int(total_posts),
                quality_tier="medium",
            )
            .on_conflict_do_update(
                index_elements=["community_name"],
                set_={
                    "crawl_priority": priority,
                    "crawl_frequency_hours": freq_hours,
                    "posts_cached": int(total_posts),
                    "total_posts_fetched": int(total_posts),
                    "last_crawled_at": datetime.now(timezone.utc),
                    "quality_tier": CommunityCache.quality_tier,
                },
            )
        )
        await db.execute(stmt)
        updated += 1

    await db.commit()
    return {"status": "completed", "updated": updated}
