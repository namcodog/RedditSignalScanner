#!/usr/bin/env python3
from __future__ import annotations

"""
Import reddit_crossborder_relevant_communities.csv into community_pool.

This script imports the 166 crossborder-relevant communities.
All communities will be categorized by their dimensions (what_to_sell, where_to_sell, how_to_sell, how_to_source).

Input CSV format:
  subreddit,post_count,earliest_post,latest_post,total_comments_count,avg_score,dimensions,relevance_score

Usage:
  cd backend && PYTHONPATH=. python scripts/import_166_crossborder_communities.py
"""

import asyncio
import csv
import ast
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.services.community_category_map_service import replace_community_category_map


def _norm(name: str) -> str:
    """Normalize subreddit name to r/xxx format and force lowercase"""
    n = (name or "").strip().lower()
    return n if n.startswith("r/") else f"r/{n}"


def _parse_dimensions(dim_str: str) -> list[str]:
    """Parse dimensions string to list"""
    try:
        # Handle string like "['where_to_sell']" or "['what_to_sell', 'how_to_sell']"
        return ast.literal_eval(dim_str)
    except:
        return []


async def main() -> None:
    # CSV文件在项目根目录
    csv_path = Path(__file__).parents[2] / "reddit_crossborder_relevant_communities.csv"

    if not csv_path.exists():
        raise SystemExit(f"❌ CSV文件不存在: {csv_path}")

    print(f"📄 读取CSV文件: {csv_path}")
    
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "name": _norm(row.get("subreddit", "")),
                    "post_count": int(row.get("post_count", 0) or 0),
                    "avg_score": float(row.get("avg_score", 0.0) or 0.0),
                    "dimensions": _parse_dimensions(row.get("dimensions", "[]")),
                    "relevance_score": int(row.get("relevance_score", 1) or 1),
                })
            except Exception as e:
                print(f"⚠️  跳过无效行: {row} - {e}")
                continue

    print(f"✅ 成功读取 {len(rows)} 个社区")
    
    async with SessionFactory() as db:
        inserted = 0
        updated = 0
        skipped = 0
        
        for r in rows:
            name = r["name"]
            if not name or name == "r/":
                skipped += 1
                continue
            
            # 根据帖子数量和平均分数计算优先级
            post_count = r["post_count"]
            avg_score = r["avg_score"]
            dimensions = r["dimensions"]
            relevance_score = r["relevance_score"]
            
            # 分层策略：
            # T1 (high): post_count >= 1000 且 avg_score >= 50
            # T2 (medium): post_count >= 500 或 avg_score >= 20
            # T3 (low): 其他
            if post_count >= 1000 and avg_score >= 50:
                tier = priority = "high"
                quality_score = 0.85
            elif post_count >= 500 or avg_score >= 20:
                tier = priority = "medium"
                quality_score = 0.70
            else:
                tier = priority = "low"
                quality_score = 0.55

            stmt = select(CommunityPool).where(CommunityPool.name == name)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            
            # 构建categories：基础类别 + dimensions
            categories = ["crossborder", "ecommerce"] + dimensions
            
            from datetime import datetime, timezone
            desc = {
                "source": "crossborder_relevant_communities_166",
                "post_count": post_count,
                "avg_score": round(avg_score, 2),
                "dimensions": dimensions,
                "relevance_score": relevance_score,
                "imported_at": datetime.now(timezone.utc).isoformat()
            }
            
            if existing:
                # 更新现有社区
                existing.tier = tier
                existing.priority = priority
                existing.description_keywords = desc
                existing.daily_posts = max(existing.daily_posts or 0, post_count // 365)  # 估算日均
                existing.quality_score = quality_score
                existing.is_active = True
                await replace_community_category_map(
                    db,
                    community_id=existing.id,
                    categories=categories,
                )
                updated += 1
            else:
                # 插入新社区
                pool = CommunityPool(
                    name=name,
                    tier=tier,
                    priority=priority,
                    categories=[],
                    description_keywords=desc,
                    daily_posts=post_count // 365,  # 估算日均帖子数
                    avg_comment_length=100,
                    quality_score=quality_score,
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
            
            if (inserted + updated) % 50 == 0:
                print(f"  进度: {inserted + updated}/{len(rows)}...")
        
        await db.commit()
    
    print(f"\n{'='*60}")
    print(f"✅ 导入完成！")
    print(f"   新增: {inserted}")
    print(f"   更新: {updated}")
    print(f"   跳过: {skipped}")
    print(f"   总计: {inserted + updated}")
    print(f"{'='*60}")
    
    # 验证导入结果
    async with SessionFactory() as db:
        stmt = select(CommunityPool).where(CommunityPool.is_active == True)
        result = await db.execute(stmt)
        total_active = len(result.scalars().all())
        print(f"\n📊 数据库活跃社区总数: {total_active}")
        
        # 按tier统计
        for t in ["high", "medium", "low"]:
            stmt = select(CommunityPool).where(
                CommunityPool.is_active == True,
                CommunityPool.tier == t
            )
            result = await db.execute(stmt)
            count = len(result.scalars().all())
            print(f"   {t.upper()}: {count}")
        
        # 按dimensions统计
        print(f"\n📊 按维度统计:")
        for dim in ["what_to_sell", "where_to_sell", "how_to_sell", "how_to_source"]:
            stmt = select(CommunityPool).where(
                CommunityPool.is_active == True,
                CommunityPool.categories.contains([dim])
            )
            result = await db.execute(stmt)
            count = len(result.scalars().all())
            print(f"   {dim}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
