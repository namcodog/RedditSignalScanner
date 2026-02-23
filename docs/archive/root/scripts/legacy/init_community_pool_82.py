#!/usr/bin/env python3
"""
修正版回填脚本：从97社区CSV回填，但排除已确认移除的15个社区，仅回填82个有效社区。

用途：修复数据断层，并实施社区治理（移除无效社区）
目标：将82个有效社区导入 community_pool，初始化 community_cache 并设置水位线

执行方式：
    python backend/scripts/backfill_community_pool_from_csv_97.py
"""
import asyncio
import csv
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Any, Set

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.community_cache import CommunityCache
from app.services.community_category_map_service import replace_community_category_map

# ============================================================================
# 配置常量
# ============================================================================

# 需要排除的社区列表（标准化为小写，不带 r/ 前缀，用于匹配）
EXCLUDED_COMMUNITIES: Set[str] = {
    # T2 (medium)
    "tiktokshopfinds",
    "shopifydropship",
    "fbaonlineretail",
    "amazonwarehousinganddelivery",
    # T3 (semantic)
    "dropshippingservice",
    "dropshippingninja",
    "dropshippingbiz",
    "anywherebutamazon",
    "amazonkdp",
    "amazonflex",
    "walmarthealth",
    "etsystrike",
    "wtf_amazon",
    "etsylistings",
    "ecommercefulfillment",
}

# CSV中的分级标签映射到系统tier
TIER_MAPPING = {
    "高价值社区": "high",      # 1000+ 帖子，全量抓取
    "次高价值社区": "medium",   # 500-999，近12个月
    "扩展语义社区": "semantic", # 100-499，近12个月仅帖子
}

# 抓取策略配置
CRAWL_STRATEGY = {
    "high": {
        "frequency_hours": 2,
        "priority": "high",
        "post_limit": 1000,
        "enable_comments": True,
    },
    "medium": {
        "frequency_hours": 4,
        "priority": "medium",
        "post_limit": 1000,
        "enable_comments": True,
    },
    "semantic": {
        "frequency_hours": 8,
        "priority": "medium",
        "post_limit": 500,
        "enable_comments": False,
    },
}

# CSV文件路径
CSV_HIGH_VALUE_PATH = Path("高价值社区池_基于165社区.csv")
CSV_MEDIUM_VALUE_PATH = Path("次高价值社区池_基于165社区.csv")
CSV_SEMANTIC_VALUE_PATH = Path("扩展语义社区池_基于165社区.csv")


# ============================================================================
# 辅助函数
# ============================================================================

def read_communities_from_csv() -> List[Dict[str, Any]]:
    """
    从分级CSV读取社区，并应用排除名单过滤
    """
    communities: List[Dict[str, Any]] = []

    def _load_from_file(path: Path, tier_label: str) -> None:
        if not path.exists():
            raise FileNotFoundError(f"CSV文件不存在: {path}")

        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue

                first_col = row[0].strip()
                if (
                    not first_col
                    or first_col.startswith("说明")
                    or first_col.startswith("抓取策略")
                    or first_col.startswith("社区分级汇总报告")
                    or first_col == "社区名称"
                ):
                    continue

                community_name = None
                for col in row:
                    col = col.strip()
                    if col.startswith("r/"):
                        community_name = col
                        break

                if not community_name:
                    continue

                # 检查是否在排除列表中
                raw_name = community_name.replace("r/", "").lower()
                if raw_name in EXCLUDED_COMMUNITIES:
                    print(f"   🚫 跳过已排除社区: {community_name}")
                    continue

                tier = TIER_MAPPING[tier_label]
                strategy = CRAWL_STRATEGY[tier]

                communities.append(
                    {
                        "name": community_name,
                        "tier_name": tier_label,
                        "tier": tier,
                        "strategy": strategy,
                    }
                )

    _load_from_file(CSV_HIGH_VALUE_PATH, "高价值社区")
    _load_from_file(CSV_MEDIUM_VALUE_PATH, "次高价值社区")
    _load_from_file(CSV_SEMANTIC_VALUE_PATH, "扩展语义社区")

    return communities


async def get_posts_stats(db, community_names: List[str]) -> Dict[str, Dict[str, Any]]:
    # 统一转为小写进行查询，以匹配数据库中的规范化数据
    raw_names_lower = [name.replace('r/', '').lower() for name in community_names]
    if not raw_names_lower:
        return {}

    # 使用 LOWER(subreddit) 确保匹配
    result = await db.execute(text('''
        SELECT
            LOWER(subreddit),
            COUNT(*) FILTER (WHERE is_current = true) as current_posts,
            COUNT(DISTINCT source_post_id) as total_posts,
            MAX(created_at) as latest_post,
            MIN(created_at) as earliest_post
        FROM posts_raw
        WHERE LOWER(subreddit) = ANY(:communities)
        GROUP BY LOWER(subreddit)
    '''), {'communities': raw_names_lower})

    stats = {}
    for row in result.fetchall():
        # key 使用小写，方便后续查找
        stats[row[0]] = {
            'current_posts': row[1],
            'total_posts': row[2],
            'latest_post': row[3],
            'earliest_post': row[4]
        }
    return stats


async def backfill_community_pool(
    db,
    communities: List[Dict[str, Any]],
    posts_stats: Dict[str, Dict[str, Any]]
) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for comm in communities:
        name = comm['name']
        tier = comm['tier']
        strategy = comm['strategy']
        existing = await db.execute(
            select(CommunityPool).where(CommunityPool.name == name)
        )
        existing_pool = existing.scalar_one_or_none()
        
        # 使用小写 key 查找统计数据
        raw_name_lower = name.replace('r/', '').lower()
        stats = posts_stats.get(raw_name_lower, {})

        if existing_pool:
            existing_pool.tier = tier
            existing_pool.priority = strategy['priority']
            existing_pool.daily_posts = stats.get('current_posts', 0)
            existing_pool.is_active = True
            updated += 1
        else:
            categories = {"source": "csv_import_82", "tier_name": comm['tier_name']}
            new_pool = CommunityPool(
                name=name,
                tier=tier,
                categories=[],
                description_keywords={},
                daily_posts=stats.get('current_posts', 0),
                avg_comment_length=100,
                quality_score=Decimal('0.50'),
                priority=strategy['priority'],
                is_active=True,
                is_blacklisted=False,
            )
            db.add(new_pool)
            await db.flush()
            await replace_community_category_map(
                db,
                community_id=new_pool.id,
                categories=categories,
            )
            inserted += 1
    return inserted, updated


async def backfill_community_cache(
    db,
    communities: List[Dict[str, Any]],
    posts_stats: Dict[str, Dict[str, Any]]
) -> tuple[int, int, int]:
    inserted = 0
    updated = 0
    skipped = 0

    for comm in communities:
        name = comm['name']
        raw_name_lower = name.replace('r/', '').lower()
        strategy = comm['strategy']
        
        # 使用小写 key 查找
        stats = posts_stats.get(raw_name_lower)

        if not stats or stats['total_posts'] == 0:
            skipped += 1
            continue

        existing = await db.execute(
            select(CommunityCache).where(CommunityCache.community_name == name)
        )
        existing_cache = existing.scalar_one_or_none()

        # 关键修改：将 last_crawled_at 设为昨天，激活调度器
        last_crawled = datetime.now(timezone.utc) - timedelta(days=1)

        if existing_cache:
            existing_cache.posts_cached = stats['current_posts']
            existing_cache.last_crawled_at = last_crawled
            existing_cache.last_seen_created_at = stats['latest_post']
            existing_cache.crawl_frequency_hours = strategy['frequency_hours']
            existing_cache.total_posts_fetched = stats['total_posts']
            existing_cache.is_active = True
            updated += 1
        else:
            new_cache = CommunityCache(
                community_name=name,
                last_crawled_at=last_crawled,
                posts_cached=stats['current_posts'],
                ttl_seconds=3600,
                quality_score=Decimal('0.50'),
                hit_count=0,
                crawl_priority=50,
                crawl_frequency_hours=strategy['frequency_hours'],
                is_active=True,
                last_seen_created_at=stats['latest_post'],
                total_posts_fetched=stats['total_posts'],
                empty_hit=0,
                success_hit=0,
                failure_hit=0,
                avg_valid_posts=0,
                quality_tier=comm['tier'], # 修复：设置初始 quality_tier
            )
            db.add(new_cache)
            inserted += 1
    return inserted, updated, skipped


async def soft_delete_excluded_communities(db) -> int:
    """将排除列表中的社区标记为 inactive"""
    count = 0
    for raw_name in EXCLUDED_COMMUNITIES:
        name = f"r/{raw_name}" if not raw_name.startswith("r/") else raw_name
        
        # Update Pool
        pool_res = await db.execute(
            select(CommunityPool).where(CommunityPool.name == name)
        )
        pool = pool_res.scalar_one_or_none()
        if pool and pool.is_active:
            pool.is_active = False
            count += 1
            print(f"   🗑️  软删除社区: {name}")
            
        # Update Cache
        cache_res = await db.execute(
            select(CommunityCache).where(CommunityCache.community_name == name)
        )
        cache = cache_res.scalar_one_or_none()
        if cache and cache.is_active:
            cache.is_active = False
            
    return count


async def main():
    print("=" * 80)
    print("🔧 82社区数据流修复：仅清理排除社区 (No CSV Mode)")
    print("=" * 80)
    print()

    print("\n🗑️  步骤1：清理排除的社区")
    try:
        async with SessionFactory() as db:
            deleted = await soft_delete_excluded_communities(db)
            await db.commit()
            print(f"   ✅ 已将 {deleted} 个排除社区标记为 inactive")
            
            # 统计剩余活跃社区
            result = await db.execute(
                select(func.count()).select_from(CommunityPool).where(CommunityPool.is_active == True)
            )
            active = result.scalar_one()
            print(f"\n✅ 最终活跃社区数: {active} (预期: 82)")
            
            if active != 82:
                print(f"⚠️  警告：活跃社区数与预期不符（{active} vs 82），请检查是否有其他未排除的杂质。")
            
    except Exception as e:
        print(f"   ❌ 清理失败: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
