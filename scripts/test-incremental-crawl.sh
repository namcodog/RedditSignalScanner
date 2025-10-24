#!/bin/bash
# 测试增量抓取功能

set -e

echo "🧪 测试增量抓取功能"
echo "===================="
echo ""

# 1. 检查数据库表是否存在
echo "1️⃣ 检查数据库表..."
psql -d reddit_signal_scanner -c "\dt posts_*" || {
    echo "❌ 数据库表不存在，请先运行迁移脚本"
    exit 1
}
echo "✅ 数据库表存在"
echo ""

# 2. 查看当前存储统计
echo "2️⃣ 当前存储统计："
    psql -d reddit_signal_scanner -c "SELECT * FROM get_storage_stats();"
echo ""

# 3. 手动触发一次增量抓取
echo "3️⃣ 手动触发增量抓取（抓取 3 个社区）..."
cd backend && python3 << 'EOF'
import asyncio
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.reddit_client import RedditAPIClient
from app.services.incremental_crawler import IncrementalCrawler

async def test_incremental_crawl():
    settings = get_settings()
    
    # 创建 Reddit 客户端
    reddit_client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
    )
    
    # 测试社区
    test_communities = ["r/Entrepreneur", "r/startups", "r/SaaS"]
    
    async with reddit_client:
        async with SessionFactory() as db:
            crawler = IncrementalCrawler(
                db=db,
                reddit_client=reddit_client,
                hot_cache_ttl_hours=24,
            )
            
            for community in test_communities:
                print(f"\n🔄 抓取 {community}...")
                result = await crawler.crawl_community_incremental(
                    community,
                    limit=50,  # 每个社区抓取 50 条
                    time_filter="month",
                )
                print(f"✅ {community}: 新增 {result['new_posts']}, 更新 {result['updated_posts']}, 去重 {result['duplicates']}")

asyncio.run(test_incremental_crawl())
EOF

echo ""
echo "4️⃣ 抓取后存储统计："
psql -d reddit_signal_scanner -c "SELECT * FROM get_storage_stats();"
echo ""

# 5. 查看冷库样本
echo "5️⃣ 冷库样本（posts_raw）："
psql -d reddit_signal_scanner -c "
SELECT 
    subreddit,
    COUNT(*) as post_count,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM posts_raw
GROUP BY subreddit
ORDER BY post_count DESC;
"
echo ""

# 6. 查看热缓存样本
echo "6️⃣ 热缓存样本（posts_hot）："
psql -d reddit_signal_scanner -c "
SELECT 
    subreddit,
    COUNT(*) as post_count,
    MIN(expires_at) as earliest_expiry,
    MAX(expires_at) as latest_expiry
FROM posts_hot
GROUP BY subreddit
ORDER BY post_count DESC;
"
echo ""

# 7. 查看水位线
echo "7️⃣ 水位线状态："
psql -d reddit_signal_scanner -c "
SELECT 
    community_name,
    last_seen_created_at,
    total_posts_fetched,
    dedup_rate,
    last_crawled_at
FROM community_cache
WHERE last_seen_created_at IS NOT NULL
ORDER BY last_crawled_at DESC
LIMIT 10;
"
echo ""

echo "🎉 测试完成！"
echo ""
echo "📊 关键指标："
echo "  - posts_raw: 冷库累积数据"
echo "  - posts_hot: 热缓存（24小时TTL）"
echo "  - 水位线: 记录最后抓取位置"
echo ""
echo "🔄 下次抓取将只拉取新于水位线的帖子（增量模式）"
