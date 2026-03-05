"""启动 24 小时 Warmup 爬取计划。

这个脚本会：
1. 加载种子社区到数据库
2. 启动 Warmup Crawler 任务
3. 配置 Celery Beat 定时任务（每 2 小时爬取一次）
4. 监控爬取进度

Usage:
    cd backend
    export $(cat .env | grep -v '^#' | xargs)
    python scripts/start_24h_warmup.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure the backend package is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.community.community_pool_loader import CommunityPoolLoader
from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.community_cache import CommunityCache
from app.tasks.warmup_crawler import warmup_crawler_task


async def load_seed_communities() -> int:
    """加载种子社区到数据库。"""
    print("=" * 60)
    print("📋 步骤 1: 加载种子社区")
    print("=" * 60)
    
    async with SessionFactory() as db:
        loader = CommunityPoolLoader(db=db)
        count = await loader.load_seed_communities()
        
        print(f"✅ 成功加载 {count} 个种子社区")
        
        # 统计各优先级社区数量
        result = await db.execute(
            select(
                CommunityPool.priority,
                func.count(CommunityPool.id).label("count")
            )
            .where(CommunityPool.is_active == True)
            .group_by(CommunityPool.priority)
            .order_by(CommunityPool.priority.desc())
        )
        
        stats = result.all()
        print("\n社区优先级分布：")
        for priority, count in stats:
            print(f"  - 优先级 {priority}: {count} 个社区")
        
        return count


async def check_existing_cache() -> dict:
    """检查现有缓存状态。"""
    print("\n" + "=" * 60)
    print("📋 步骤 2: 检查现有缓存")
    print("=" * 60)
    
    async with SessionFactory() as db:
        # 统计缓存记录
        result = await db.execute(
            select(func.count(CommunityCache.id))
        )
        total_cached = result.scalar() or 0
        
        # 统计最近 24 小时的缓存
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await db.execute(
            select(func.count(CommunityCache.id))
            .where(CommunityCache.cached_at >= cutoff)
        )
        recent_cached = result.scalar() or 0
        
        # 统计总帖子数
        result = await db.execute(
            select(func.sum(CommunityCache.post_count))
        )
        total_posts = result.scalar() or 0
        
        stats = {
            "total_cached_communities": total_cached,
            "recent_cached_communities": recent_cached,
            "total_posts": total_posts,
        }
        
        print(f"缓存统计：")
        print(f"  - 总缓存社区数: {total_cached}")
        print(f"  - 最近 24 小时缓存: {recent_cached}")
        print(f"  - 总帖子数: {total_posts}")
        
        if total_cached > 0:
            # 显示最近缓存的社区
            result = await db.execute(
                select(CommunityCache)
                .order_by(CommunityCache.cached_at.desc())
                .limit(5)
            )
            recent = result.scalars().all()
            
            print(f"\n最近缓存的社区：")
            for cache in recent:
                age = datetime.now(timezone.utc) - cache.cached_at
                hours = age.total_seconds() / 3600
                print(f"  - r/{cache.community_name}: {cache.post_count} 帖子 ({hours:.1f} 小时前)")
        
        return stats


def start_warmup_crawler() -> str:
    """启动 Warmup Crawler 任务。"""
    print("\n" + "=" * 60)
    print("📋 步骤 3: 启动 Warmup Crawler")
    print("=" * 60)
    
    try:
        # 提交 Celery 任务
        result = warmup_crawler_task.delay()
        task_id = result.id
        
        print(f"✅ Warmup Crawler 任务已提交")
        print(f"   任务 ID: {task_id}")
        print(f"   预计耗时: 10-30 分钟（取决于社区数量）")
        print(f"\n监控任务进度：")
        print(f"   tail -f /tmp/celery_worker.log | grep -E '(warmup|crawl)'")
        
        return task_id
    
    except Exception as e:
        print(f"❌ 启动 Warmup Crawler 失败: {e}")
        print(f"\n请确保 Celery Worker 正在运行：")
        print(f"   ps aux | grep celery")
        raise


async def monitor_progress(task_id: str, duration_minutes: int = 30) -> None:
    """监控爬取进度。"""
    print("\n" + "=" * 60)
    print(f"📋 步骤 4: 监控爬取进度（{duration_minutes} 分钟）")
    print("=" * 60)
    
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    last_count = 0
    
    while datetime.now(timezone.utc) < end_time:
        async with SessionFactory() as db:
            # 统计缓存记录
            result = await db.execute(
                select(func.count(CommunityCache.id))
            )
            current_count = result.scalar() or 0
            
            # 统计总帖子数
            result = await db.execute(
                select(func.sum(CommunityCache.post_count))
            )
            total_posts = result.scalar() or 0
            
            # 计算进度
            elapsed = datetime.now(timezone.utc) - start_time
            elapsed_minutes = elapsed.total_seconds() / 60
            
            new_communities = current_count - last_count
            last_count = current_count
            
            print(f"[{elapsed_minutes:.1f} 分钟] 已缓存 {current_count} 个社区，{total_posts} 条帖子", end="")
            if new_communities > 0:
                print(f" (+{new_communities} 新增)", end="")
            print()
        
        # 每 30 秒检查一次
        await asyncio.sleep(30)
    
    print(f"\n✅ 监控完成")


async def print_final_stats() -> None:
    """打印最终统计。"""
    print("\n" + "=" * 60)
    print("📊 最终统计")
    print("=" * 60)
    
    async with SessionFactory() as db:
        # 总缓存社区数
        result = await db.execute(
            select(func.count(CommunityCache.id))
        )
        total_cached = result.scalar() or 0
        
        # 总帖子数
        result = await db.execute(
            select(func.sum(CommunityCache.post_count))
        )
        total_posts = result.scalar() or 0
        
        # 平均每个社区的帖子数
        avg_posts = total_posts / total_cached if total_cached > 0 else 0
        
        print(f"总缓存社区数: {total_cached}")
        print(f"总帖子数: {total_posts}")
        print(f"平均每个社区帖子数: {avg_posts:.1f}")
        
        # 显示前 10 个社区
        result = await db.execute(
            select(CommunityCache)
            .order_by(CommunityCache.post_count.desc())
            .limit(10)
        )
        top_communities = result.scalars().all()
        
        print(f"\n前 10 个社区（按帖子数）：")
        for i, cache in enumerate(top_communities, 1):
            print(f"  {i}. r/{cache.community_name}: {cache.post_count} 帖子")


async def main() -> None:
    """主函数。"""
    print("=" * 60)
    print("🚀 启动 24 小时 Warmup 爬取计划")
    print("=" * 60)
    print()
    
    try:
        # 1. 加载种子社区
        count = await load_seed_communities()
        
        if count == 0:
            print("❌ 没有加载到种子社区，退出")
            sys.exit(1)
        
        # 2. 检查现有缓存
        stats = await check_existing_cache()
        
        # 3. 启动 Warmup Crawler
        task_id = start_warmup_crawler()
        
        # 4. 监控进度（可选）
        print("\n是否监控爬取进度？(y/n): ", end="")
        choice = input().strip().lower()
        
        if choice == "y":
            print("监控时长（分钟，默认 30）: ", end="")
            duration_input = input().strip()
            duration = int(duration_input) if duration_input else 30
            
            await monitor_progress(task_id, duration)
            await print_final_stats()
        else:
            print("\n✅ Warmup Crawler 已在后台运行")
            print(f"\n查看进度：")
            print(f"   tail -f /tmp/celery_worker.log | grep -E '(warmup|crawl)'")
            print(f"\n查看缓存统计：")
            print(f"   psql -d reddit_scanner -c \"SELECT COUNT(*) FROM community_cache;\"")
        
        print("\n" + "=" * 60)
        print("✅ 24 小时 Warmup 爬取计划已启动！")
        print("=" * 60)
        print()
        print("📝 下一步：")
        print("   1. Warmup Crawler 将在后台持续运行")
        print("   2. 每 2 小时自动爬取一次（由 Celery Beat 调度）")
        print("   3. 缓存数据将保存到 Redis 和 PostgreSQL")
        print("   4. 你可以开始使用前端提交真实的分析任务")
        print()
        print("🔍 验证缓存：")
        print("   psql -d reddit_scanner -c \"SELECT community_name, post_count, cached_at FROM community_cache ORDER BY cached_at DESC LIMIT 10;\"")
        print()
    
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

