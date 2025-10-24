#!/bin/bash

# Day 15 - Excel 导入功能端到端测试
# Lead 严格验收脚本

set -e

echo "=========================================="
echo "Day 15 Excel 导入功能端到端测试"
echo "=========================================="
echo ""

PROJECT_ROOT="/Users/hujia/Desktop/RedditSignalScanner"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$PROJECT_ROOT"

echo "1️⃣ 环境检查"
echo "----------------------------------------"

# 检查 Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis 未运行"
    exit 1
fi
echo "✅ Redis 运行中"

# 检查 PostgreSQL
if ! psql -U postgres -h localhost -d reddit_scanner -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ PostgreSQL 未运行或数据库不存在"
    exit 1
fi
echo "✅ PostgreSQL 运行中"

echo ""
echo "2️⃣ 代码语法检查"
echo "----------------------------------------"

cd "$BACKEND_DIR"

# 检查 Python 语法
python -m py_compile app/services/community_import_service.py
echo "✅ community_import_service.py 语法正确"

python -m py_compile app/api/routes/admin_communities.py
echo "✅ admin_communities.py 语法正确"

python -m py_compile tests/test_community_import.py
echo "✅ test_community_import.py 语法正确"

echo ""
echo "3️⃣ 单元测试"
echo "----------------------------------------"

export APP_ENV=test
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/reddit_signal_scanner"

pytest tests/test_community_import.py -v --tb=short

echo ""
echo "4️⃣ 模板生成测试"
echo "----------------------------------------"

python << 'EOF'
import sys
sys.path.insert(0, '.')
from app.services.community_import_service import CommunityImportService

# 测试模板生成
template = CommunityImportService.generate_template()
print(f'✅ 模板生成成功: {len(template)} bytes')

# 保存到临时文件
with open('/tmp/test_community_template.xlsx', 'wb') as f:
    f.write(template)
print('✅ 模板已保存到 /tmp/test_community_template.xlsx')

# 验证模板可读
import pandas as pd
df = pd.read_excel('/tmp/test_community_template.xlsx')
print(f'✅ 模板包含 {len(df)} 行示例数据')
print(f'✅ 列名: {list(df.columns)}')

# 验证必填列
required_columns = ['name', 'tier', 'categories', 'description_keywords']
for col in required_columns:
    if col not in df.columns:
        print(f'❌ 缺少必填列: {col}')
        sys.exit(1)
print(f'✅ 所有必填列存在')

# 验证示例数据
if len(df) < 3:
    print(f'❌ 示例数据不足 3 行')
    sys.exit(1)
print(f'✅ 示例数据充足')

# 验证第一行数据
first_row = df.iloc[0]
if not first_row['name'].startswith('r/'):
    print(f'❌ 第一行社区名称格式错误: {first_row["name"]}')
    sys.exit(1)
print(f'✅ 示例数据格式正确')

print('')
print('📊 模板内容预览:')
print(df.head())
EOF

echo ""
echo "5️⃣ 导入功能测试（dry_run=True）"
echo "----------------------------------------"

python << 'EOF'
import asyncio
import sys
import uuid
sys.path.insert(0, '.')

from app.services.community_import_service import CommunityImportService
from app.db.session import async_session_maker

async def test_dry_run():
    # 读取模板文件
    with open('/tmp/test_community_template.xlsx', 'rb') as f:
        content = f.read()
    
    async with async_session_maker() as session:
        service = CommunityImportService(session)
        
        # 测试 dry_run=True（仅验证）
        print('🔍 测试仅验证模式（dry_run=True）')
        result = await service.import_from_excel(
            content=content,
            filename='test_template.xlsx',
            dry_run=True,
            actor_email='admin@test.com',
            actor_id=uuid.uuid4()
        )
        
        print(f'状态: {result["status"]}')
        print(f'摘要: {result["summary"]}')
        
        if result['status'] != 'validated':
            print(f'❌ 验证失败: {result.get("errors", [])}')
            sys.exit(1)
        
        print('✅ 验证通过')
        
        # 验证摘要数据
        summary = result['summary']
        if summary['total'] != 3:
            print(f'❌ 总数错误: {summary["total"]}')
            sys.exit(1)
        
        if summary['valid'] < 1:
            print(f'❌ 有效数量错误: {summary["valid"]}')
            sys.exit(1)
        
        print(f'✅ 摘要数据正确: {summary}')

asyncio.run(test_dry_run())
EOF

echo ""
echo "6️⃣ 导入功能测试（dry_run=False）"
echo "----------------------------------------"

python << 'EOF'
import asyncio
import sys
import uuid
sys.path.insert(0, '.')

from app.services.community_import_service import CommunityImportService
from app.db.session import async_session_maker
from sqlalchemy import select
from app.models.community_pool import CommunityPool

async def test_actual_import():
    # 读取模板文件
    with open('/tmp/test_community_template.xlsx', 'rb') as f:
        content = f.read()
    
    async with async_session_maker() as session:
        service = CommunityImportService(session)
        
        # 清理测试数据
        await session.execute(
            select(CommunityPool).where(CommunityPool.name.in_(['r/startups', 'r/Entrepreneur', 'r/SaaS']))
        )
        test_communities = (await session.execute(
            select(CommunityPool).where(CommunityPool.name.in_(['r/startups', 'r/Entrepreneur', 'r/SaaS']))
        )).scalars().all()
        
        for comm in test_communities:
            await session.delete(comm)
        await session.commit()
        print('✅ 测试数据已清理')
        
        # 测试实际导入
        print('💾 测试实际导入模式（dry_run=False）')
        result = await service.import_from_excel(
            content=content,
            filename='test_template.xlsx',
            dry_run=False,
            actor_email='admin@test.com',
            actor_id=uuid.uuid4()
        )
        
        print(f'状态: {result["status"]}')
        print(f'摘要: {result["summary"]}')
        
        if result['status'] != 'success':
            print(f'❌ 导入失败: {result.get("errors", [])}')
            sys.exit(1)
        
        print('✅ 导入成功')
        
        # 验证数据库
        imported_communities = (await session.execute(
            select(CommunityPool).where(CommunityPool.name.in_(['r/startups', 'r/Entrepreneur', 'r/SaaS']))
        )).scalars().all()
        
        if len(imported_communities) < 1:
            print(f'❌ 数据库中未找到导入的社区')
            sys.exit(1)
        
        print(f'✅ 数据库验证通过: 找到 {len(imported_communities)} 个社区')
        
        for comm in imported_communities:
            print(f'  - {comm.name} ({comm.tier})')

asyncio.run(test_actual_import())
EOF

echo ""
echo "7️⃣ 重复导入测试"
echo "----------------------------------------"

python << 'EOF'
import asyncio
import sys
import uuid
sys.path.insert(0, '.')

from app.services.community_import_service import CommunityImportService
from app.db.session import async_session_maker

async def test_duplicate_import():
    # 读取模板文件
    with open('/tmp/test_community_template.xlsx', 'rb') as f:
        content = f.read()
    
    async with async_session_maker() as session:
        service = CommunityImportService(session)
        
        # 测试重复导入
        print('🔄 测试重复导入检测')
        result = await service.import_from_excel(
            content=content,
            filename='test_template_duplicate.xlsx',
            dry_run=False,
            actor_email='admin@test.com',
            actor_id=uuid.uuid4()
        )
        
        print(f'状态: {result["status"]}')
        print(f'摘要: {result["summary"]}')
        
        # 应该检测到重复
        if result['summary']['duplicates'] == 0:
            print(f'❌ 未检测到重复社区')
            sys.exit(1)
        
        print(f'✅ 重复检测正常: {result["summary"]["duplicates"]} 个重复')
        
        if 'errors' in result and len(result['errors']) > 0:
            print(f'✅ 错误信息详细:')
            for err in result['errors'][:3]:
                print(f'  - 第{err["row"]}行: {err["error"]}')

asyncio.run(test_duplicate_import())
EOF

echo ""
echo "=========================================="
echo "✅ 所有测试通过！"
echo "=========================================="
echo ""
echo "📊 测试总结:"
echo "  ✅ 环境检查通过"
echo "  ✅ 代码语法正确"
echo "  ✅ 单元测试通过"
echo "  ✅ 模板生成正常"
echo "  ✅ 仅验证模式正常"
echo "  ✅ 实际导入正常"
echo "  ✅ 重复检测正常"
echo ""
echo "🎉 Excel 导入功能验收通过！"
