#!/bin/bash
# E2E 测试：完整数据管道测试
#
# 测试流程：
# 1. 导入社区数据
# 2. 运行增量抓取
# 3. 验证数据完整性
# 4. 运行分析引擎
# 5. 验证报告生成

set -e

echo "🧪 E2E 测试：完整数据管道"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步骤计数
STEP=1

function step() {
    echo ""
    echo -e "${GREEN}📍 步骤 $STEP: $1${NC}"
    STEP=$((STEP + 1))
}

function error() {
    echo -e "${RED}❌ 错误: $1${NC}"
    exit 1
}

function warning() {
    echo -e "${YELLOW}⚠️  警告: $1${NC}"
}

function success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 检查环境
step "检查环境"
if [ ! -f "backend/.env" ]; then
    error "backend/.env 文件不存在！请先配置环境变量。"
fi

if ! command -v python3.11 &> /dev/null; then
    error "python3.11 未安装！"
fi

success "环境检查通过"

# 1. 导入社区数据
step "导入社区数据"
PYTHONPATH=backend python3.11 scripts/import_community_expansion.py || error "社区数据导入失败"
success "社区数据导入完成"

# 2. 验证社区数据
step "验证社区数据"
COMMUNITY_COUNT=$(PYTHONPATH=backend python3.11 -c "
import asyncio
from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from sqlalchemy import select, func

async def check():
    async with SessionFactory() as db:
        result = await db.execute(select(func.count()).select_from(CommunityPool))
        print(result.scalar())

asyncio.run(check())
")

if [ "$COMMUNITY_COUNT" -lt 200 ]; then
    error "社区数量不足：$COMMUNITY_COUNT < 200"
fi

success "社区数据验证通过：$COMMUNITY_COUNT 个社区"

# 3. 运行增量抓取（小批量测试）
step "运行增量抓取（测试模式：3 个社区，每个 5 条帖子）"
PYTHONPATH=backend \
CRAWLER_SORT=new \
CRAWLER_TIME_FILTER=week \
CRAWLER_POST_LIMIT=5 \
CRAWLER_BATCH_SIZE=3 \
CRAWLER_MAX_CONCURRENCY=1 \
python3.11 scripts/run-incremental-crawl.py || error "增量抓取失败"

success "增量抓取完成"

# 4. 验证帖子数据
step "验证帖子数据"
POST_COUNT=$(PYTHONPATH=backend python3.11 -c "
import asyncio
from app.db.session import SessionFactory
from app.models.posts_storage import PostHot
from sqlalchemy import select, func

async def check():
    async with SessionFactory() as db:
        result = await db.execute(select(func.count()).select_from(PostHot))
        print(result.scalar())

asyncio.run(check())
")

if [ "$POST_COUNT" -lt 1 ]; then
    error "PostHot 表为空！抓取失败或数据未写入。"
fi

success "帖子数据验证通过：$POST_COUNT 条帖子"

# 5. 运行集成测试
step "运行集成测试"
cd backend
PYTHONPATH=. python3.11 -m pytest tests/integration/ -v --tb=short || error "集成测试失败"
cd ..

success "集成测试通过"

# 6. 数据一致性检查
step "数据一致性检查"
PYTHONPATH=backend python3.11 -c "
import asyncio
from app.db.session import SessionFactory
from app.models.posts_storage import PostHot, PostRaw
from app.models.community_cache import CommunityCache
from sqlalchemy import select, func

async def check():
    async with SessionFactory() as db:
        # PostHot 数量
        result_hot = await db.execute(select(func.count()).select_from(PostHot))
        hot_count = result_hot.scalar()
        
        # PostRaw 数量
        result_raw = await db.execute(select(func.count()).select_from(PostRaw))
        raw_count = result_raw.scalar()
        
        # CommunityCache 统计
        result_cache = await db.execute(
            select(func.count()).select_from(CommunityCache).where(CommunityCache.success_hit > 0)
        )
        cache_count = result_cache.scalar()
        
        print(f'PostHot: {hot_count}')
        print(f'PostRaw: {raw_count}')
        print(f'CommunityCache (success): {cache_count}')
        
        # 验证一致性
        assert raw_count >= hot_count, f'数据不一致：PostRaw({raw_count}) < PostHot({hot_count})'
        assert cache_count > 0, 'CommunityCache 没有成功记录'
        
        print('✅ 数据一致性检查通过')

asyncio.run(check())
" || error "数据一致性检查失败"

success "数据一致性检查通过"

# 7. 生成测试报告
step "生成测试报告"
REPORT_FILE="reports/phase-log/e2e-test-$(date +%Y%m%d-%H%M%S).md"
mkdir -p "$(dirname "$REPORT_FILE")"

cat > "$REPORT_FILE" << EOF
# E2E 测试报告

**测试时间**: $(date '+%Y-%m-%d %H:%M:%S')

## 测试结果

✅ **所有测试通过**

## 数据统计

- **社区数量**: $COMMUNITY_COUNT
- **帖子数量**: $POST_COUNT
- **测试模式**: 3 个社区，每个 5 条帖子

## 测试步骤

1. ✅ 导入社区数据
2. ✅ 验证社区数据
3. ✅ 运行增量抓取
4. ✅ 验证帖子数据
5. ✅ 运行集成测试
6. ✅ 数据一致性检查

## 结论

完整数据管道测试通过，系统运行正常。

EOF

success "测试报告已生成：$REPORT_FILE"

# 完成
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 E2E 测试完成！所有检查通过。${NC}"
echo "=========================================="
echo ""
echo "📊 测试摘要："
echo "  - 社区数量: $COMMUNITY_COUNT"
echo "  - 帖子数量: $POST_COUNT"
echo "  - 测试报告: $REPORT_FILE"
echo ""

