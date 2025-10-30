from __future__ import annotations

"""
DB helper: summarize community cache status.

Outputs totals and a small sample to stdout and writes a snapshot JSON
under reports/local-acceptance/.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Select, select, func, desc

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache


async def main() -> int:
    async with SessionFactory() as s:
        total = int(await s.scalar(select(func.count(CommunityCache.community_name))) or 0)
        active = int(
            await s.scalar(
                select(func.count(CommunityCache.community_name)).where(
                    CommunityCache.is_active.is_(True)
                )
            )
            or 0
        )
        with_posts = int(
            await s.scalar(
                select(func.count(CommunityCache.community_name)).where(
                    CommunityCache.posts_cached > 0
                )
            )
            or 0
        )

        cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
        fresh = int(
            await s.scalar(
                select(func.count(CommunityCache.community_name)).where(
                    CommunityCache.last_crawled_at >= cutoff
                )
            )
            or 0
        )

        stmt: Select[Any] = (
            select(
                CommunityCache.community_name,
                CommunityCache.posts_cached,
                CommunityCache.hit_count,
                CommunityCache.last_crawled_at,
                CommunityCache.crawl_frequency_hours,
            )
            .order_by(desc(CommunityCache.posts_cached))
            .limit(10)
        )
        rows = (await s.execute(stmt)).all()
        sample = [
            {
                "name": r.community_name,
                "posts_cached": int(r.posts_cached or 0),
                "hit_count": int(r.hit_count or 0),
                "last_crawled_at": r.last_crawled_at.isoformat() if r.last_crawled_at else None,
                "freq_h": int(r.crawl_frequency_hours or 0) if r.crawl_frequency_hours is not None else None,
            }
            for r in rows
        ]

    payload = {
        "total_entries": total,
        "active_entries": active,
        "entries_with_posts": with_posts,
        "fresh_within_6h": fresh,
        "sample_top10": sample,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    out = Path(__file__).resolve().parents[2] / "reports" / "local-acceptance"
    out.mkdir(parents=True, exist_ok=True)
    (out / "community-cache-stats.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

