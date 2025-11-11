#!/usr/bin/env python3
from __future__ import annotations

"""
Import hybrid_score_communities.csv into community_pool for crossborder theme.

This bridges Spec 011 semantics back to the community pool so TieredScheduler
and crawler can pick them up. Scores are mapped to priority/tier.

Input CSV (produced by score_with_hybrid_reddit.py):
  subreddit,layer,posts,coverage,density,purity,mentions,score

Usage:
  python -u backend/scripts/import_hybrid_scores_to_pool.py \
    --csv backend/reports/local-acceptance/hybrid_score_communities.csv
"""

import argparse
import asyncio
import csv
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool


def _norm(name: str) -> str:
    n = (name or "").strip()
    return n if n.startswith("r/") else f"r/{n}"


async def main() -> None:
    ap = argparse.ArgumentParser(description="Import hybrid score CSV into community_pool")
    ap.add_argument("--csv", type=Path, default=Path("backend/reports/local-acceptance/hybrid_score_communities.csv"))
    args = ap.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"Input CSV not found: {args.csv}")

    rows: list[dict[str, Any]] = []
    with args.csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "name": _norm(row.get("subreddit", "")),
                    "score": float(row.get("score", 0.0) or 0.0),
                    "layer": row.get("layer", "L1"),
                })
            except Exception:
                continue

    async with SessionFactory() as db:
        inserted = 0
        updated = 0
        for r in rows:
            name = r["name"]
            score0_1 = max(0.0, min(1.0, r["score"] / 100.0))
            # Map score to priority
            if score0_1 >= 0.75:
                priority = tier = "high"
            elif score0_1 >= 0.45:
                priority = tier = "medium"
            else:
                priority = tier = "low"

            stmt = select(CommunityPool).where(CommunityPool.name == name)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            categories = ["crossborder", f"crossborder:hybrid", f"layer:{r['layer']}"]
            from datetime import datetime, timezone
            desc = {"source": "hybrid_scoring", "score": round(score0_1, 3), "scored_at": datetime.now(timezone.utc).isoformat()}
            if existing:
                existing.tier = tier
                existing.priority = priority
                existing.categories = categories
                existing.description_keywords = desc
                existing.is_active = True
                updated += 1
            else:
                db.add(CommunityPool(
                    name=name,
                    tier=tier,
                    priority=priority,
                    categories=categories,
                    description_keywords=desc,
                    daily_posts=0,
                    avg_comment_length=100,
                    quality_score=float(score0_1),
                    is_active=True,
                ))
                inserted += 1
        await db.commit()
    print(f"✅ Imported hybrid scores → pool (inserted={inserted}, updated={updated})")


if __name__ == "__main__":
    asyncio.run(main())
