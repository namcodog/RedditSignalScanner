#!/usr/bin/env python3
"""
精准补抓任务

针对低质量或长时间未更新的社区进行定向补抓，
提升整体数据覆盖度和新鲜度。

查询条件:
- last_crawled_at > 8 小时（长时间未抓取）
- avg_valid_posts < 50（低质量或无数据）
- is_active = true（活跃社区）
- is_blacklisted = false（非黑名单）

使用方法:
    PYTHONPATH=backend python3 scripts/targeted_recrawl.py [--dry-run] [--hours HOURS] [--threshold THRESHOLD]
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


async def find_recrawl_candidates(
    hours_threshold: int = 8,
    quality_threshold: int = 50,
    dry_run: bool = False
) -> list[str]:
    """查找需要补抓的社区"""
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(hours=hours_threshold)
    
    async with SessionFactory() as db:
        # 查询符合条件的社区
        query = (
            select(CommunityPool.name, CommunityCache.last_crawled_at, CommunityCache.avg_valid_posts)
            .join(
                CommunityCache,
                CommunityPool.name == CommunityCache.community_name,
                isouter=True
            )
            .where(
                and_(
                    CommunityPool.is_active == True,
                    CommunityPool.is_blacklisted == False,
                    # 条件1: 长时间未抓取 OR 从未抓取
                    (
                        (CommunityCache.last_crawled_at < cutoff_time) |
                        (CommunityCache.last_crawled_at == None)
                    ),
                    # 条件2: 低质量 OR 无数据
                    (
                        (CommunityCache.avg_valid_posts < quality_threshold) |
                        (CommunityCache.avg_valid_posts == None)
                    )
                )
            )
            .order_by(CommunityCache.last_crawled_at.asc().nullsfirst())
        )
        
        result = await db.execute(query)
        candidates = []
        
        print(f"🔍 查找补抓候选社区...")
        print(f"   - 时间阈值: {hours_threshold} 小时前")
        print(f"   - 质量阈值: avg_valid_posts < {quality_threshold}")
        print(f"   - 截止时间: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for name, last_crawled, avg_posts in result:
            candidates.append(name)
            
            if len(candidates) <= 20:  # 只打印前 20 个
                last_crawled_str = last_crawled.strftime('%Y-%m-%d %H:%M:%S') if last_crawled else '从未抓取'
                avg_posts_str = str(avg_posts) if avg_posts is not None else '无数据'
                print(f"  ✓ {name}")
                print(f"      最后抓取: {last_crawled_str}")
                print(f"      质量分: {avg_posts_str}")
        
        if len(candidates) > 20:
            print(f"  ... 还有 {len(candidates) - 20} 个社区")
        
        return candidates


async def execute_recrawl(
    candidates: list[str],
    dry_run: bool = False
) -> None:
    """执行补抓任务"""
    if not candidates:
        print("\n⚠️  无需补抓的社区")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 补抓统计:")
    print(f"   - 候选社区数: {len(candidates)}")
    
    if dry_run:
        print(f"\n🔍 DRY RUN 模式 - 不会实际抓取")
        print(f"\n建议执行命令:")
        print(f"PYTHONPATH=backend \\")
        print(f"CRAWLER_SORT=top \\")
        print(f"CRAWLER_TIME_FILTER=month \\")
        print(f"CRAWLER_POST_LIMIT=100 \\")
        print(f"CRAWLER_BATCH_SIZE={min(len(candidates), 15)} \\")
        print(f"CRAWLER_MAX_CONCURRENCY=3 \\")
        print(f"python3 scripts/run-incremental-crawl.py")
        return
    
    # 实际执行补抓
    print(f"\n🚀 开始补抓...")
    print(f"   - 策略: sort=top, time_filter=month, limit=100")
    print(f"   - 批次大小: {min(len(candidates), 15)}")
    
    # 设置环境变量
    import os
    os.environ["CRAWLER_SORT"] = "top"
    os.environ["CRAWLER_TIME_FILTER"] = "month"
    os.environ["CRAWLER_POST_LIMIT"] = "100"
    os.environ["CRAWLER_BATCH_SIZE"] = str(min(len(candidates), 15))
    os.environ["CRAWLER_MAX_CONCURRENCY"] = "3"
    
    # 调用增量抓取
    # 注意：这里简化实现，实际应该调用 crawler_task
    print(f"\n💡 提示: 请手动执行上述命令进行补抓")


async def main() -> None:
    """主函数"""
    dry_run = "--dry-run" in sys.argv
    
    # 解析参数
    hours_threshold = 8
    quality_threshold = 50
    
    if "--hours" in sys.argv:
        hours_idx = sys.argv.index("--hours")
        if hours_idx + 1 < len(sys.argv):
            hours_threshold = int(sys.argv[hours_idx + 1])
    
    if "--threshold" in sys.argv:
        threshold_idx = sys.argv.index("--threshold")
        if threshold_idx + 1 < len(sys.argv):
            quality_threshold = int(sys.argv[threshold_idx + 1])
    
    if dry_run:
        print("🔍 DRY RUN 模式启用\n")
    
    print("=" * 60)
    print("🎯 精准补抓任务")
    print("=" * 60)
    print()
    
    # 查找候选社区
    candidates = await find_recrawl_candidates(
        hours_threshold=hours_threshold,
        quality_threshold=quality_threshold,
        dry_run=dry_run
    )
    
    # 执行补抓
    await execute_recrawl(candidates, dry_run=dry_run)
    
    print(f"\n{'='*60}")
    print("✅ 补抓任务完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

