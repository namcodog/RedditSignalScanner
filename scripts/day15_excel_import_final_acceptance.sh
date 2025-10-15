#!/bin/bash
set -e

echo "============================================================"
echo "Day 15 Excel 导入功能 - Lead 最终验收"
echo "============================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 验收结果
PASSED=0
FAILED=0

# 测试函数
test_step() {
    local step_name="$1"
    local command="$2"
    
    echo "----------------------------------------"
    echo "🔍 $step_name"
    echo "----------------------------------------"
    
    if eval "$command"; then
        echo -e "${GREEN}✅ $step_name - 通过${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ $step_name - 失败${NC}"
        ((FAILED++))
        return 1
    fi
}

cd "$(dirname "$0")/.."

echo "步骤 1：代码语法检查"
test_step "语法检查" "cd backend && python -m py_compile app/services/community_import_service.py app/api/routes/admin_communities.py"

echo ""
echo "步骤 2：数据库表验证"
test_step "数据库表存在" "psql -U postgres -h localhost -d reddit_scanner -c '\d community_import_history' > /dev/null 2>&1"

echo ""
echo "步骤 3：单元测试"
test_step "单元测试" "cd backend && export APP_ENV=test && python -m pytest tests/test_community_import.py -q --tb=no"

echo ""
echo "步骤 4：模板生成测试"
cat > /tmp/test_template.py << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.services.community_import_service import CommunityImportService
import pandas as pd

# 生成模板
template = CommunityImportService.generate_template()
assert len(template) > 0, "模板为空"

# 保存并验证
with open('/tmp/test_template.xlsx', 'wb') as f:
    f.write(template)

# 读取验证
df = pd.read_excel('/tmp/test_template.xlsx')
assert len(df) == 3, f"示例行数错误: {len(df)}"
assert 'name' in df.columns, "缺少 name 列"
assert 'tier' in df.columns, "缺少 tier 列"
assert 'categories' in df.columns, "缺少 categories 列"
assert 'description_keywords' in df.columns, "缺少 description_keywords 列"

print("✅ 模板生成成功")
EOF

test_step "模板生成" "python /tmp/test_template.py"

echo ""
echo "步骤 5：API 路由注册验证"
cat > /tmp/test_routes.py << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.main import app

# 检查路由是否注册
routes = [route.path for route in app.routes]
assert '/api/admin/communities/template' in routes, "模板下载路由未注册"
assert '/api/admin/communities/import' in routes, "导入路由未注册"
assert '/api/admin/communities/import-history' in routes, "导入历史路由未注册"

print("✅ 所有 API 路由已注册")
EOF

test_step "API 路由注册" "python /tmp/test_routes.py"

echo ""
echo "步骤 6：导入服务功能测试"
cat > /tmp/test_import_service.py << 'EOF'
import sys
import asyncio
import uuid
sys.path.insert(0, 'backend')

from app.services.community_import_service import CommunityImportService
from app.db.session import async_session_maker

async def test():
    # 读取模板
    with open('/tmp/test_template.xlsx', 'rb') as f:
        content = f.read()
    
    async with async_session_maker() as session:
        service = CommunityImportService(session)
        
        # 测试验证（dry_run=True）
        result = await service.import_from_excel(
            content=content,
            filename='test.xlsx',
            dry_run=True,
            actor_email='test@test.com',
            actor_id=uuid.uuid4()
        )
        
        assert result['status'] in ['success', 'validated'], f"验证失败: {result}"
        assert 'summary' in result, "缺少 summary"
        
        print(f"✅ 导入服务测试通过: {result['status']}")

asyncio.run(test())
EOF

test_step "导入服务功能" "python /tmp/test_import_service.py"

echo ""
echo "============================================================"
echo "验收总结"
echo "============================================================"
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 所有验收测试通过！${NC}"
    exit 0
else
    echo -e "${RED}❌ 验收失败，请修复问题后重新验收${NC}"
    exit 1
fi

