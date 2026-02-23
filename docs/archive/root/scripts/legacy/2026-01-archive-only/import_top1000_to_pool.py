#!/usr/bin/env python3
from __future__ import annotations

"""
Import backend/data/top1000_subreddits.json into community_pool.

The JSON schema is the same as used by CommunityPoolLoader's optional baseline:
  {
    "communities": [
      {
        "name": "r/AmazonSeller",
        "domain_label": "...",
        "quality_score": 0.72,
        "categories": ["..."],
        "priority": "high|medium|low"  # optional
        ...
      }
    ]
  }

Usage:
  python backend/scripts/import_top1000_to_pool.py \
    --source backend/data/top1000_subreddits.json
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.services.community_category_map_service import replace_community_category_map


def _norm_name(n: str) -> str:
    n = (n or "").strip()
    return n if n.startswith("r/") else f"r/{n}" if n else n


def _tier_from_quality(q: float) -> str:
    if q >= 0.8:
        return "high"
    if q >= 0.6:
        return "medium"
    return "low"


async def import_top1000(path: Path) -> Dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    communities = payload.get("communities") or payload.get("seed_communities") or []
    stats = {"inserted": 0, "updated": 0, "total": 0}

    async with SessionFactory() as db:
        for item in communities:
            name = _norm_name(str(item.get("name", "")))
            if not name:
                continue
            quality = float(item.get("quality_score", 0.6) or 0.6)
            tier = str(item.get("tier") or _tier_from_quality(quality))
            priority = str(item.get("priority") or tier)
            cats = item.get("categories") or []
            categories = ["crossborder_top1000"] + [c for c in cats if isinstance(c, str)]
            desc = item.get("description_keywords") or {"source": "top1000"}

            stmt = select(CommunityPool).where(CommunityPool.name == name)
            existing: CommunityPool | None = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.tier = tier
                existing.priority = priority
                existing.description_keywords = desc
                existing.daily_posts = existing.daily_posts or int(item.get("estimated_daily_posts", 0) or 0)
                existing.avg_comment_length = existing.avg_comment_length or 100
                existing.quality_score = quality
                existing.is_active = True
                await replace_community_category_map(
                    db,
                    community_id=existing.id,
                    categories=categories,
                )
                stats["updated"] += 1
            else:
                pool = CommunityPool(
                    name=name,
                    tier=tier,
                    priority=priority,
                    categories=[],
                    description_keywords=desc,
                    daily_posts=int(item.get("estimated_daily_posts", 0) or 0),
                    avg_comment_length=100,
                    quality_score=quality,
                    is_active=True,
                )
                db.add(pool)
                await db.flush()
                await replace_community_category_map(
                    db,
                    community_id=pool.id,
                    categories=categories,
                )
                stats["inserted"] += 1
        await db.commit()

    stats["total"] = stats["inserted"] + stats["updated"]
    return stats


def main() -> None:  # pragma: no cover - simple CLI
    ap = argparse.ArgumentParser(description="Import top1000_subreddits.json into community_pool")
    ap.add_argument("--source", type=Path, default=Path("backend/data/top1000_subreddits.json"))
    args = ap.parse_args()
    import asyncio

    res = asyncio.run(import_top1000(args.source))
    print(f"✅ Imported top1000 into community_pool: {res}")


if __name__ == "__main__":
    main()
