#!/usr/bin/env python3
"""
混合恢复脚本：Community Pool 灾难恢复

用途：当 community_pool 被意外清空时，利用 "CSV配置" (业务真理) + "posts_raw" (数据事实) 重建大脑。
策略：
1. 优先信赖 CSV 中的 82 个有效社区配置（Tier/Priority）。
2. 使用数据库中的 posts_raw 计算真实水位线 (Last Seen)。
3. 对于 DB 中存在但 CSV 中没有的社区（Ghost Communities），如果数据量足够，也进行抢救性恢复（标记为 recovered）。
4. 激活调度器（Set last_crawled_at = yesterday）。

执行方式：
    python backend/scripts/import/restore_pool_hybrid.py
"""
import argparse
import asyncio
import csv
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Set

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, text
from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.community_cache import CommunityCache
from scripts.import_safety import add_execute_flag, ensure_dev_or_test_database, is_dry_run

# ============================================================================
# 配置常量 (复用之前的治理逻辑)
# ============================================================================

EXCLUDED_COMMUNITIES: Set[str] = {
    "tiktokshopfinds", "shopifydropship", "fbaonlineretail", "amazonwarehousinganddelivery",
    "dropshippingservice", "dropshippingninja", "dropshippingbiz", "anywherebutamazon",
    "amazonkdp", "amazonflex", "walmarthealth", "etsystrike", "wtf_amazon",
    "etsylistings", "ecommercefulfillment",
}

TIER_MAPPING = {
    "高价值社区": "high",
    "次高价值社区": "medium",
    "扩展语义社区": "semantic",
}

# CSV文件路径
CSV_HIGH_VALUE_PATH = Path("高价值社区池_基于165社区.csv")
CSV_MEDIUM_VALUE_PATH = Path("次高价值社区池_基于165社区.csv")
CSV_SEMANTIC_VALUE_PATH = Path("扩展语义社区池_基于165社区.csv")

# ============================================================================
# 核心逻辑
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Restore community_pool from CSV truth + posts_raw assets")
    add_execute_flag(parser)
    parser.add_argument(
        "--allow-ghost-recovery",
        action="store_true",
        help="允许把 CSV 外的 ghost 社区重新拉回 pool/cache。默认关闭。",
    )
    return parser

def read_csv_config() -> Dict[str, Dict[str, Any]]:
    """读取 CSV 配置，返回 {raw_name: config} 字典"""
    configs = {}

    def _load(path: Path, tier_label: str):
        if not path.exists():
            print(f"⚠️  CSV文件缺失: {path}")
            return
        
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row: continue
                first = row[0].strip()
                if not first or first.startswith(("说明", "抓取策略", "社区分级", "社区名称")):
                    continue
                
                name = None
                for col in row:
                    if col.strip().startswith("r/"):
                        name = col.strip()
                        break
                
                if not name: continue
                
                raw_name = name.replace("r/", "").lower() # Key 使用小写 raw_name
                if raw_name in EXCLUDED_COMMUNITIES:
                    continue
                
                tier = TIER_MAPPING.get(tier_label, "medium")
                priority = "high" if tier == "high" else "medium"
                
                configs[raw_name] = {
                    "name": name, # 保留原始大小写和前缀
                    "tier": tier,
                    "priority": priority,
                    "source": "csv_config"
                }

    _load(CSV_HIGH_VALUE_PATH, "高价值社区")
    _load(CSV_MEDIUM_VALUE_PATH, "次高价值社区")
    _load(CSV_SEMANTIC_VALUE_PATH, "扩展语义社区")
    
    return configs

async def scan_database_assets(db) -> Dict[str, Dict[str, Any]]:
    """扫描 posts_raw，返回 {raw_name: stats}"""
    print("🔍 扫描 posts_raw 表重建资产清单...")
    
    # 聚合查询：每个社区的帖子数、最新时间
    stmt = text("""
        SELECT 
            subreddit, 
            COUNT(*) as count, 
            MAX(created_at) as last_seen,
            MAX(fetched_at) as last_fetched
        FROM posts_raw 
        WHERE subreddit IS NOT NULL AND subreddit != ''
        GROUP BY subreddit
    """)
    
    result = await db.execute(stmt)
    assets = {}
    
    for row in result.fetchall():
        raw_name = row[0].strip().lower()
        assets[raw_name] = {
            "raw_name": row[0], # 数据库里的原始写法
            "count": row[1],
            "last_seen": row[2],
            "last_fetched": row[3]
        }
    
    return assets

async def restore_process(
    db,
    *,
    execute: bool,
    allow_ghost_recovery: bool,
) -> Dict[str, int]:
    # 1. 获取两份真理
    csv_configs = read_csv_config() # 期望的状态 (82个)
    db_assets = await scan_database_assets(db) # 实际的状态 (可能更多或更少)
    
    print(f"📊 CSV 配置社区数: {len(csv_configs)}")
    print(f"📊 DB 存量社区数: {len(db_assets)}")
    
    restored_count = 0
    recovered_count = 0
    ghosts_blocked = 0
    
    # 2. 恢复 CSV 中的社区 (优先)
    for raw_name, config in csv_configs.items():
        # 查找对应的 DB 数据
        asset = db_assets.get(raw_name)
        
        # 准备 Pool 数据
        pool = CommunityPool(
            name=config["name"],
            tier=config["tier"],
            priority=config["priority"],
            categories=[],
            description_keywords={},
            daily_posts=asset["count"] if asset else 0, # 暂时用总量代替 daily
            avg_comment_length=100,
            quality_score=Decimal("0.8") if config["tier"] == "high" else Decimal("0.5"),
            is_active=True,
            is_blacklisted=False
        )
        
        # 准备 Cache 数据
        last_seen = asset["last_seen"] if asset else None
        # 激活调度：昨天
        last_crawled = datetime.now(timezone.utc) - timedelta(days=1)
        
        cache = CommunityCache(
            community_name=config["name"],
            last_crawled_at=last_crawled,
            posts_cached=asset["count"] if asset else 0,
            last_seen_created_at=last_seen,
            crawl_frequency_hours=2 if config["tier"] == "high" else 8,
            is_active=True,
            total_posts_fetched=asset["count"] if asset else 0,
            quality_tier=config["tier"]
        )

        if execute:
            await upsert_pool(db, pool)
            await upsert_cache(db, cache)
        restored_count += 1
        
    # 3. DB 中有但 CSV 没有的社区（Ghost）默认不恢复，只做统计
    for raw_name, asset in db_assets.items():
        if raw_name in csv_configs:
            continue # 已处理
        
        if raw_name in EXCLUDED_COMMUNITIES:
            continue # 明确排除
            
        if asset["count"] < 100:
            continue # 数据太少，忽略
            
        if not allow_ghost_recovery:
            ghosts_blocked += 1
            continue

        # 这是一个“幽灵社区”，只有显式 allow 才抢救恢复
        real_name = f"r/{asset['raw_name']}" # 尽量加前缀
        
        print(f"👻 发现幽灵社区 (DB有/CSV无): {real_name} (帖子数: {asset['count']}) -> 抢救恢复为 T3")
        
        pool = CommunityPool(
            name=real_name,
            tier="semantic", # 默认为 T3
            priority="low",
            categories=[],
            description_keywords={},
            daily_posts=0,
            avg_comment_length=0,
            quality_score=Decimal("0.3"),
            is_active=True, # 激活它
            is_blacklisted=False
        )
        
        cache = CommunityCache(
            community_name=real_name,
            last_crawled_at=datetime.now(timezone.utc) - timedelta(days=1),
            posts_cached=asset["count"],
            last_seen_created_at=asset["last_seen"],
            crawl_frequency_hours=24,
            is_active=True,
            total_posts_fetched=asset["count"],
            quality_tier="semantic"
        )

        if execute:
            await upsert_pool(db, pool)
            await upsert_cache(db, cache)
        recovered_count += 1

    if execute:
        await db.commit()
    else:
        await db.rollback()

    return {
        "restored": restored_count,
        "recovered": recovered_count,
        "ghosts_blocked": ghosts_blocked,
    }

async def upsert_pool(db, item: CommunityPool):
    """幂等写入 Pool"""
    stmt = select(CommunityPool).where(CommunityPool.name == item.name)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        # 恢复关键字段
        existing.is_active = True
        existing.tier = item.tier
        existing.priority = item.priority
    else:
        db.add(item)

async def upsert_cache(db, item: CommunityCache):
    """幂等写入 Cache"""
    stmt = select(CommunityCache).where(CommunityCache.community_name == item.community_name)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.is_active = True
        # 强制重置 last_crawled_at 以激活调度，但保留 last_seen_created_at 水位线（如果有更旧的）
        existing.last_crawled_at = item.last_crawled_at
        if item.last_seen_created_at:
             existing.last_seen_created_at = item.last_seen_created_at
    else:
        db.add(item)

async def main():
    args = build_parser().parse_args()
    db_name = ensure_dev_or_test_database()
    dry_run = is_dry_run(args)

    print("🚨 开始执行混合恢复脚本...")
    print(f"🛡️  目标数据库: {db_name}")
    print("🧪 当前模式: dry-run（只预览，不写库）" if dry_run else "✍️ 当前模式: execute（将实际写库）")
    if not args.allow_ghost_recovery:
        print("🧹 Ghost 恢复默认关闭：CSV 外社区不会被拉回 pool/cache")
    try:
        async with SessionFactory() as db:
            summary = await restore_process(
                db,
                execute=not dry_run,
                allow_ghost_recovery=args.allow_ghost_recovery,
            )
            print("-" * 40)
            print("🧪 Dry-run 完成报告:" if dry_run else "✅ 恢复完成报告:")
            print(f"   - CSV配置恢复 (Standard): {summary['restored']} 个")
            print(f"   - DB幽灵抢救 (Ghost):    {summary['recovered']} 个")
            print(f"   - Ghost默认拦截:         {summary['ghosts_blocked']} 个")
            print(f"   - 总计激活社区:          {summary['restored'] + summary['recovered']} 个")
            print("-" * 40)
    except Exception as e:
        print(f"❌ 恢复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
