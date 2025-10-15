#!/usr/bin/env python3
"""
Day 14 缓存预热脚本
直接调用爬虫任务，无需启动 Celery Beat/Worker
用于测试前快速预热缓存
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# 加载 .env 文件
from dotenv import load_dotenv
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ 已加载环境变量：{env_file}")
else:
    print(f"⚠️  未找到 .env 文件：{env_file}")

from app.tasks.crawler_task import _crawl_seeds_impl


async def main():
    print("=" * 60)
    print("Day 14 缓存预热 - 开始")
    print("=" * 60)
    print()
    print("📋 任务说明：")
    print("  - 爬取所有种子社区（100 个）")
    print("  - 每个社区获取 100 个帖子")
    print("  - 批量大小：12 个社区/批次")
    print("  - 并发限制：5 个社区同时爬取")
    print("  - 预计耗时：10-20 分钟")
    print()
    print("⚠️  注意：")
    print("  - 需要配置 Reddit API 凭证（.env 文件）")
    print("  - 需要 Redis 和 PostgreSQL 运行中")
    print("  - API 限流：60 次/分钟")
    print()
    
    confirm = input("是否开始预热？(y/N): ")
    if confirm.lower() != 'y':
        print("❌ 已取消")
        return
    
    print()
    print("🚀 开始爬取...")
    print()
    
    try:
        result = await _crawl_seeds_impl(force_refresh=False)
        
        print()
        print("=" * 60)
        print("✅ 预热完成")
        print("=" * 60)
        print()
        print(f"📊 统计：")
        print(f"  - 总社区数：{result.get('total', 0)}")
        print(f"  - 成功：{result.get('succeeded', 0)}")
        print(f"  - 失败：{result.get('failed', 0)}")
        print()
        
        if result.get('failed', 0) > 0:
            print("❌ 失败的社区：")
            for item in result.get('communities', []):
                if item.get('status') == 'failed':
                    print(f"  - {item.get('community')}: {item.get('error')}")
            print()
        
        print("✅ 缓存已预热，可以运行测试了！")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ 预热失败")
        print("=" * 60)
        print()
        print(f"错误：{e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

