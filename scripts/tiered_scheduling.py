#!/usr/bin/env python3
"""
分级调度策略实现

根据社区质量分（avg_valid_posts）将社区分为三档，
并应用不同的抓取策略（频率、sort、time_filter）。

使用方法:
    PYTHONPATH=backend python3 scripts/tiered_scheduling.py [--dry-run] [--tier TIER]
"""
import asyncio
import sys
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.blacklist_loader import get_blacklist_config


# 分级策略配置
TIER_CONFIG = {
    "tier1": {
        "name": "高活跃（Tier 1）",
        "threshold_min": 20,  # avg_valid_posts > 20
        "threshold_max": None,
        "frequency_hours": 2,
        "sort": "new",
        "time_filter": "week",
        "limit": 50,
        "description": "高质量高活跃社区，优先抓取最新内容",
    },
    "tier2": {
        "name": "中活跃（Tier 2）",
        "threshold_min": 10,  # 10 < avg_valid_posts ≤ 20
        "threshold_max": 20,
        "frequency_hours": 6,
        "sort": "top",
        "time_filter": "week",
        "limit": 80,
        "description": "中等质量社区，平衡热门与新增",
    },
    "tier3": {
        "name": "低活跃（Tier 3）",
        "threshold_min": 0,  # avg_valid_posts ≤ 10
        "threshold_max": 10,
        "frequency_hours": 24,
        "sort": "top",
        "time_filter": "month",
        "limit": 100,
        "description": "低活跃社区，覆盖历史内容",
    },
}


async def calculate_tier_assignment(dry_run: bool = False) -> dict[str, list[str]]:
    """计算社区分级分配"""
    blacklist_config = get_blacklist_config()
    
    async with SessionFactory() as db:
        # 获取所有活跃社区（排除黑名单）
        result = await db.execute(
            select(CommunityPool.name, CommunityPool.is_blacklisted)
            .where(CommunityPool.is_active == True)
        )
        all_communities = {name: is_blacklisted for name, is_blacklisted in result}
        
        # 获取 community_cache 中的质量数据
        result = await db.execute(
            select(CommunityCache.community_name, CommunityCache.avg_valid_posts)
        )
        quality_data = {name: avg_posts for name, avg_posts in result}
        
        # 分级分配
        tier_assignments: dict[str, list[str]] = {
            "tier1": [],
            "tier2": [],
            "tier3": [],
            "no_data": [],
            "blacklisted": [],
        }
        
        for community_name, is_blacklisted in all_communities.items():
            # 跳过黑名单社区
            if is_blacklisted or blacklist_config.is_community_blacklisted(community_name):
                tier_assignments["blacklisted"].append(community_name)
                continue
            
            # 获取质量分
            avg_valid_posts = quality_data.get(community_name, 0)
            
            # 无数据的社区（未抓取过）
            if avg_valid_posts == 0:
                tier_assignments["no_data"].append(community_name)
                continue
            
            # 分级
            if avg_valid_posts > TIER_CONFIG["tier1"]["threshold_min"]:
                tier_assignments["tier1"].append(community_name)
            elif avg_valid_posts > TIER_CONFIG["tier2"]["threshold_min"]:
                tier_assignments["tier2"].append(community_name)
            else:
                tier_assignments["tier3"].append(community_name)
        
        return tier_assignments


async def apply_tier_to_cache(tier_assignments: dict[str, list[str]], dry_run: bool = False) -> None:
    """将分级结果应用到 community_cache 表"""
    async with SessionFactory() as db:
        updated_count = 0
        
        for tier_name, communities in tier_assignments.items():
            if tier_name in ["no_data", "blacklisted"]:
                continue
            
            frequency_hours = TIER_CONFIG[tier_name]["frequency_hours"]
            
            for community_name in communities:
                if not dry_run:
                    await db.execute(
                        update(CommunityCache)
                        .where(CommunityCache.community_name == community_name)
                        .values(
                            crawl_frequency_hours=frequency_hours,
                            quality_tier=tier_name,
                        )
                    )
                    updated_count += 1
        
        if not dry_run:
            await db.commit()
            print(f"✅ 已更新 {updated_count} 个社区的调度配置")


async def run_tiered_crawl(tier: str, dry_run: bool = False) -> None:
    """执行指定档位的抓取任务"""
    if tier not in TIER_CONFIG:
        print(f"❌ 无效的 tier: {tier}")
        return
    
    tier_config = TIER_CONFIG[tier]
    tier_assignments = await calculate_tier_assignment(dry_run=True)
    communities = tier_assignments.get(tier, [])
    
    if not communities:
        print(f"⚠️  {tier_config['name']} 无社区")
        return
    
    print(f"\n🎯 执行 {tier_config['name']} 抓取")
    print(f"   - 社区数: {len(communities)}")
    print(f"   - 频率: 每 {tier_config['frequency_hours']} 小时")
    print(f"   - 策略: sort={tier_config['sort']}, time_filter={tier_config['time_filter']}, limit={tier_config['limit']}")
    
    if dry_run:
        print(f"\n🔍 DRY RUN 模式 - 不会实际抓取")
        print(f"\n前 10 个社区:")
        for name in communities[:10]:
            print(f"  - {name}")
        return
    
    # 实际抓取逻辑（调用增量抓取）
    import os
    os.environ["CRAWLER_SORT"] = tier_config["sort"]
    os.environ["CRAWLER_TIME_FILTER"] = tier_config["time_filter"]
    os.environ["CRAWLER_POST_LIMIT"] = str(tier_config["limit"])
    os.environ["CRAWLER_BATCH_SIZE"] = str(min(len(communities), 15))
    
    print(f"\n🚀 开始抓取...")
    # 这里可以调用 crawler_task 或 run-incremental-crawl.py
    # 为了简化，我们只打印命令
    print(f"\n建议执行命令:")
    print(f"PYTHONPATH=backend CRAWLER_SORT={tier_config['sort']} "
          f"CRAWLER_TIME_FILTER={tier_config['time_filter']} "
          f"CRAWLER_POST_LIMIT={tier_config['limit']} "
          f"python3 scripts/run-incremental-crawl.py")


async def main() -> None:
    """主函数"""
    dry_run = "--dry-run" in sys.argv
    tier = None
    
    # 解析 --tier 参数
    if "--tier" in sys.argv:
        tier_idx = sys.argv.index("--tier")
        if tier_idx + 1 < len(sys.argv):
            tier = sys.argv[tier_idx + 1]
    
    if dry_run:
        print("🔍 DRY RUN 模式启用\n")
    
    # 计算分级分配
    tier_assignments = await calculate_tier_assignment(dry_run=dry_run)
    
    # 打印分级统计
    print("=" * 60)
    print("📊 社区分级统计")
    print("=" * 60)
    
    for tier_name, tier_config in TIER_CONFIG.items():
        communities = tier_assignments.get(tier_name, [])
        print(f"\n{tier_config['name']}:")
        print(f"  社区数: {len(communities)}")
        print(f"  阈值: avg_valid_posts {tier_config['threshold_min']} - {tier_config['threshold_max'] or '∞'}")
        print(f"  频率: 每 {tier_config['frequency_hours']} 小时")
        print(f"  策略: sort={tier_config['sort']}, time_filter={tier_config['time_filter']}, limit={tier_config['limit']}")
        print(f"  说明: {tier_config['description']}")
        
        if communities and len(communities) <= 10:
            print(f"  社区: {', '.join(communities)}")
        elif communities:
            print(f"  示例: {', '.join(communities[:5])}...")
    
    # 无数据社区
    no_data = tier_assignments.get("no_data", [])
    print(f"\n⚪ 无数据社区（未抓取过）:")
    print(f"  社区数: {len(no_data)}")
    if no_data and len(no_data) <= 10:
        print(f"  社区: {', '.join(no_data)}")
    
    # 黑名单社区
    blacklisted = tier_assignments.get("blacklisted", [])
    print(f"\n🚫 黑名单社区:")
    print(f"  社区数: {len(blacklisted)}")
    if blacklisted:
        print(f"  社区: {', '.join(blacklisted)}")
    
    # 应用分级配置到数据库
    if not dry_run:
        print(f"\n{'='*60}")
        await apply_tier_to_cache(tier_assignments, dry_run=dry_run)
    
    # 如果指定了 tier，执行该档位的抓取
    if tier:
        await run_tiered_crawl(tier, dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())

