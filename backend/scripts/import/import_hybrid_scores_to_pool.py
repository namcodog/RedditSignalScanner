#!/usr/bin/env python3
from __future__ import annotations

"""
Import hybrid_score_communities.csv into community_pool for crossborder theme.

This bridges Spec 011 semantics back to the community pool so TieredScheduler
and crawler can pick them up. Scores are mapped to priority/tier.

Input CSV (produced by score_with_hybrid_reddit.py):
  subreddit,layer,posts,coverage,density,purity,mentions,score

Usage:
  python -u backend/scripts/import/import_hybrid_scores_to_pool.py \
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
from app.services.community.community_category_map_service import replace_community_category_map
from scripts.import_safety import add_execute_flag, ensure_dev_or_test_database, is_dry_run


def _norm(name: str) -> str:
    n = (name or "").strip()
    return n if n.startswith("r/") else f"r/{n}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import hybrid score CSV into community_pool")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("backend/reports/local-acceptance/hybrid_score_communities.csv"),
    )
    add_execute_flag(parser)
    return parser


async def _run_import(*, csv_path: Path, execute: bool) -> tuple[int, int]:
    if not csv_path.exists():
        raise SystemExit(f"Input CSV not found: {csv_path}")

    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append(
                    {
                        "name": _norm(row.get("subreddit", "")),
                        "score": float(row.get("score", 0.0) or 0.0),
                        "layer": row.get("layer", "L1"),
                    }
                )
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
            desc = {
                "source": "hybrid_scoring",
                "score": round(score0_1, 3),
                "scored_at": datetime.now(timezone.utc).isoformat(),
            }
            if existing:
                if execute:
                    existing.tier = tier
                    existing.priority = priority
                    existing.description_keywords = desc
                    existing.is_active = True
                    await replace_community_category_map(
                        db,
                        community_id=existing.id,
                        categories=categories,
                    )
                updated += 1
            else:
                if execute:
                    pool = CommunityPool(
                        name=name,
                        tier=tier,
                        priority=priority,
                        categories=[],
                        description_keywords=desc,
                        daily_posts=0,
                        avg_comment_length=100,
                        quality_score=float(score0_1),
                        is_active=True,
                    )
                    db.add(pool)
                    await db.flush()
                    await replace_community_category_map(
                        db,
                        community_id=pool.id,
                        categories=categories,
                    )
                inserted += 1
        if execute:
            await db.commit()
        else:
            await db.rollback()
    return inserted, updated


async def main() -> None:
    args = build_parser().parse_args()
    db_name = ensure_dev_or_test_database()
    dry_run = is_dry_run(args)

    print(f"🛡️  目标数据库: {db_name}")
    print("🧪 当前模式: dry-run（只预览，不写库）" if dry_run else "✍️ 当前模式: execute（将实际写库）")

    inserted, updated = await _run_import(csv_path=args.csv, execute=not dry_run)
    status = "🧪 Dry-run 完成" if dry_run else "✅ 导入完成"
    print(f"{status} → hybrid scores (inserted={inserted}, updated={updated})")


if __name__ == "__main__":
    asyncio.run(main())
