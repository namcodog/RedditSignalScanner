#!/bin/bash
# 启用真实 Reddit API 并开始 24 小时社区池数据爬取缓存

set -e

echo "=========================================="
echo "🚀 启用真实 Reddit API 并开始数据爬取"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 步骤 1: 检查环境变量
echo "📋 步骤 1/5: 检查 Reddit API 凭证"
echo "---"

cd backend
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

if [ -z "$REDDIT_CLIENT_ID" ] || [ -z "$REDDIT_CLIENT_SECRET" ]; then
    echo -e "${RED}❌ Reddit API 凭证未配置${NC}"
    echo -e "${YELLOW}请在 backend/.env 中配置：${NC}"
    echo "  REDDIT_CLIENT_ID=your_client_id"
    echo "  REDDIT_CLIENT_SECRET=your_client_secret"
    exit 1
fi

echo -e "${GREEN}✅ Reddit API 凭证已配置${NC}"
echo -e "${YELLOW}   Client ID: ${REDDIT_CLIENT_ID:0:10}...${NC}"
echo ""

# 步骤 2: 加载种子社区到数据库
echo "📋 步骤 2/5: 加载种子社区到数据库"
echo "---"

if /opt/homebrew/bin/python3.11 -c "
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from app.services.community_pool_loader import CommunityPoolLoader
from app.db.session import SessionFactory

async def load():
    async with SessionFactory() as db:
        loader = CommunityPoolLoader(db=db)
        count = await loader.load_seed_communities()
        print(f'✅ 加载了 {count} 个种子社区')
        return count

result = asyncio.run(load())
sys.exit(0 if result > 0 else 1)
"; then
    echo -e "${GREEN}✅ 种子社区加载成功${NC}"
else
    echo -e "${RED}❌ 种子社区加载失败${NC}"
    cd ..
    exit 1
fi

echo ""

# 步骤 3: 启动 Warmup Crawler（24 小时爬取任务）
echo "📋 步骤 3/5: 启动 24 小时社区池数据爬取"
echo "---"

echo -e "${YELLOW}正在启动 Warmup Crawler...${NC}"

# 使用 Celery Beat 调度 warmup_crawler 任务
# 每 2 小时爬取一次（可根据缓存命中率自动调整）
if /opt/homebrew/bin/python3.11 -c "
import asyncio
from app.tasks.warmup_crawler import warmup_crawler_task

# 立即执行一次全量爬取
result = warmup_crawler_task.delay()
print(f'✅ Warmup Crawler 任务已提交: {result.id}')
print('   任务将在后台执行，预计需要 10-30 分钟')
"; then
    echo -e "${GREEN}✅ Warmup Crawler 已启动${NC}"
else
    echo -e "${YELLOW}⚠️  Warmup Crawler 启动失败（可能 Celery Worker 未运行）${NC}"
fi

echo ""

# 步骤 4: 验证 Reddit API 连接
echo "📋 步骤 4/5: 验证 Reddit API 连接"
echo "---"

if /opt/homebrew/bin/python3.11 -c "
import asyncio
from app.services.reddit_client import RedditAPIClient
from app.core.config import settings

async def test_reddit_api():
    client = RedditAPIClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )
    
    async with client:
        # 测试搜索功能
        posts = await client.search_posts('python programming', limit=5)
        print(f'✅ Reddit API 连接成功，获取到 {len(posts)} 条帖子')
        if posts:
            print(f'   示例帖子: {posts[0].title[:50]}...')
        return len(posts) > 0

result = asyncio.run(test_reddit_api())
exit(0 if result else 1)
"; then
    echo -e "${GREEN}✅ Reddit API 连接正常${NC}"
else
    echo -e "${RED}❌ Reddit API 连接失败${NC}"
    echo -e "${YELLOW}请检查：${NC}"
    echo "  1. Reddit API 凭证是否正确"
    echo "  2. 网络连接是否正常"
    echo "  3. Reddit API 是否可访问"
    cd ..
    exit 1
fi

echo ""

# 步骤 5: 查看爬取进度
echo "📋 步骤 5/5: 查看爬取进度"
echo "---"

echo -e "${YELLOW}查看 Celery Worker 日志以监控爬取进度：${NC}"
echo "  tail -f /tmp/celery_worker.log | grep -E '(warmup|crawl|reddit)'"
echo ""
echo -e "${YELLOW}查看数据库中的缓存数据：${NC}"
echo "  psql -d reddit_scanner -c \"SELECT community_name, post_count, cached_at FROM community_cache ORDER BY cached_at DESC LIMIT 10;\""
echo ""

cd ..

echo "=========================================="
echo "✅ 真实 Reddit API 已启用！"
echo "=========================================="
echo ""
echo "📊 下一步："
echo "   1. 监控 Celery Worker 日志查看爬取进度"
echo "   2. 等待 10-30 分钟让 Warmup Crawler 完成首次爬取"
echo "   3. 使用前端提交真实的分析任务进行端到端测试"
echo ""
echo "🔍 验证缓存："
echo "   psql -d reddit_scanner -c \"SELECT COUNT(*) FROM community_cache;\""
echo ""
echo "📝 查看爬取统计："
echo "   psql -d reddit_scanner -c \"SELECT community_name, post_count, cached_at FROM community_cache ORDER BY post_count DESC LIMIT 20;\""
echo ""

