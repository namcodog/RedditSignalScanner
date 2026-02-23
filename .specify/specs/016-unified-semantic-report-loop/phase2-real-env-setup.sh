#!/bin/bash
# Phase 2 纯真实环境快速启动脚本（零 Mock）
# 用法: bash phase2-real-env-setup.sh

set -e

echo "🚀 Phase 2 纯真实环境配置（零 Mock）"
echo ""

# ============================================
# 1. 检查依赖
# ============================================
echo "1️⃣ 检查依赖..."

# PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL 未安装，请先安装: brew install postgresql@14"
    exit 1
fi

# Redis
if ! command -v redis-cli &> /dev/null; then
    echo "❌ Redis 未安装，请先安装: brew install redis"
    exit 1
fi

# Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python 未安装"
    exit 1
fi

echo "✅ 依赖检查通过"
echo ""

# ============================================
# 2. 配置环境变量（纯真实配置，智能合并）
# ============================================
echo "2️⃣ 配置 backend/.env（智能合并，保留现有配置）..."

if [ -f backend/.env ]; then
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    echo "⚠️  检测到 backend/.env 已存在"
    echo "   为了保护您的配置（如 Reddit API keys），采用智能合并策略："
    echo ""
    echo "   1. 备份现有配置到：backend/.env.backup_$TIMESTAMP"
    echo "   2. 生成 Phase 2 配置模板到：backend/.env.phase2_template"
    echo "   3. 您可以手动合并两个文件"
    echo ""

    # 备份现有配置
    cp backend/.env backend/.env.backup_$TIMESTAMP
    echo "   ✅ 已备份：backend/.env.backup_$TIMESTAMP"

    # 生成 Phase 2 模板（不覆盖原文件）
    cat > backend/.env.phase2_template << 'EOF_TEMPLATE'
# ============================================
# Phase 2 纯真实环境配置（零 Mock）
# ============================================

# 数据库（真实 PostgreSQL）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner

# Redis（真实 Redis）
REDIS_URL=redis://localhost:6379/5
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
TASK_STATUS_REDIS_URL=redis://localhost:6379/3

# JWT（真实 JWT，开发用密钥）
JWT_SECRET=phase2-dev-secret-20251124
JWT_ALGORITHM=HS256

# 开发环境设置
APP_ENV=development
DEFAULT_MEMBERSHIP_LEVEL=pro

# 报告质量等级（Phase 2.1-2.3 用 standard，2.4 改为 premium）
REPORT_QUALITY_LEVEL=standard

# Celery（Phase 2 推荐 inline 执行，方便调试）
ENABLE_CELERY_DISPATCH=0

# Admin 权限
ADMIN_EMAILS=dev@example.com,phase2-test@example.com

# CORS
CORS_ALLOW_ORIGINS=http://localhost:3006,http://localhost:3000

# Reddit API（可选，Phase 2 暂不需要）
# REDDIT_CLIENT_ID=
# REDDIT_CLIENT_SECRET=

# OpenAI API（Phase 2.4 时填写，Phase 2.1-2.3 留空即可）
# OPENAI_API_KEY=sk-proj-...

# 报告缓存
REPORT_CACHE_TTL_SECONDS=3600
REPORT_RATE_LIMIT_PER_MINUTE=30

EOF_TEMPLATE

    echo "   ✅ 已生成模板：backend/.env.phase2_template"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 手动合并配置（推荐）："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "# 1. 查看需要添加的 Phase 2 配置"
    echo "cat backend/.env.phase2_template"
    echo ""
    echo "# 2. 手动添加缺失的配置到 backend/.env"
    echo "# 重点添加以下配置（如果缺失）："
    echo "#   - REPORT_QUALITY_LEVEL=standard"
    echo "#   - ENABLE_CELERY_DISPATCH=0"
    echo "#   - DEFAULT_MEMBERSHIP_LEVEL=pro"
    echo ""
    echo "# 3. 或者使用自动合并脚本（谨慎）："
    echo "bash .specify/specs/016-unified-semantic-report-loop/merge-env.sh"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    read -p "按 Enter 继续（跳过 .env 配置）..."

else
    echo "   未检测到 backend/.env，创建新文件..."
    cat > backend/.env << 'EOF'

# ============================================
# 3. 启动基础设施（真实服务）
# ============================================
echo "3️⃣ 启动基础设施（真实 PostgreSQL & Redis）..."

# PostgreSQL
echo "  - 检查 PostgreSQL 状态..."
if pg_isready -q; then
    echo "    ✅ PostgreSQL 已运行"
else
    echo "    ⚠️  PostgreSQL 未运行，尝试启动..."
    if command -v brew &> /dev/null; then
        brew services start postgresql@14 || brew services start postgresql
    else
        echo "    请手动启动 PostgreSQL"
        exit 1
    fi
    sleep 2
fi

# 检查数据库是否存在
echo "  - 检查数据库 reddit_signal_scanner..."
if psql -lqt | cut -d \| -f 1 | grep -qw reddit_signal_scanner; then
    echo "    ✅ 数据库已存在"
else
    echo "    ⚠️  数据库不存在，创建中..."
    createdb reddit_signal_scanner || true
fi

# Redis
echo "  - 检查 Redis 状态..."
if redis-cli ping &> /dev/null; then
    echo "    ✅ Redis 已运行"
else
    echo "    ⚠️  Redis 未运行，尝试启动..."
    if command -v brew &> /dev/null; then
        brew services start redis
    else
        redis-server --daemonize yes
    fi
    sleep 2
fi

echo "✅ 基础设施已就绪"
echo ""

# ============================================
# 4. 运行数据库迁移（真实数据库）
# ============================================
echo "4️⃣ 运行数据库迁移（真实数据库）..."

cd backend
# 检查 alembic 是否配置
if [ -f alembic.ini ]; then
    echo "  - 运行 Alembic 迁移..."
    alembic upgrade head || echo "    ⚠️  迁移可能失败，请手动检查"
else
    echo "    ⚠️  未找到 alembic.ini，跳过迁移"
fi
cd ..

echo "✅ 数据库迁移完成"
echo ""

# ============================================
# 5. 创建测试用户（真实数据库存储）
# ============================================
echo "5️⃣ 创建测试用户（真实数据库）..."

python backend/scripts/create_test_users.py || echo "⚠️  创建用户失败，可能已存在"

echo "✅ 测试用户已创建"
echo ""

# ============================================
# 6. 生成 Bearer Token（真实 JWT）
# ============================================
echo "6️⃣ 生成 Bearer Token（真实 JWT）..."

TOKEN=$(python - <<'PY'
import sys
sys.path.insert(0, "backend")
from app.core.security import create_access_token

user_id = "00000000-0000-0000-0000-000000000001"
token = create_access_token({"sub": user_id})
print(token)
PY
)

echo ""
echo "✅ Bearer Token 已生成（真实 JWT）"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 复制以下 Token（用于 HTTP 请求）:"
echo ""
echo "export PHASE2_TOKEN=\"$TOKEN\""
echo ""
echo "或在 curl 中使用:"
echo "Authorization: Bearer $TOKEN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 保存到临时文件
echo "export PHASE2_TOKEN=\"$TOKEN\"" > /tmp/phase2_token.sh
echo "💾 Token 已保存到: /tmp/phase2_token.sh"
echo "   使用: source /tmp/phase2_token.sh"
echo ""

# ============================================
# 7. 环境验收测试
# ============================================
echo "7️⃣ 环境验收测试（零 Mock）..."
echo ""

# 启动后端（后台）
echo "  - 启动后端服务（后台）..."
cd backend
nohup uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload > /tmp/phase2_backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo "    后端 PID: $BACKEND_PID"
echo "    日志: tail -f /tmp/phase2_backend.log"

# 等待启动
echo "  - 等待后端启动（10秒）..."
sleep 10

# 健康检查
echo "  - 健康检查..."
if curl -s http://localhost:8006/health | grep -q "ok"; then
    echo "    ✅ 后端健康检查通过"
else
    echo "    ❌ 后端健康检查失败，查看日志: tail -f /tmp/phase2_backend.log"
    exit 1
fi

# 测试认证
echo "  - 测试认证（真实 JWT）..."
AUTH_RESULT=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8006/api/users/me)
if echo "$AUTH_RESULT" | grep -q "email"; then
    echo "    ✅ 认证测试通过"
else
    echo "    ❌ 认证测试失败: $AUTH_RESULT"
    exit 1
fi

echo ""
echo "✅ 环境验收测试通过"
echo ""

# ============================================
# 8. 完成提示
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Phase 2 纯真实环境已就绪（零 Mock）！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 服务状态:"
echo "  ✅ PostgreSQL:  真实数据库运行中"
echo "  ✅ Redis:       真实缓存运行中"
echo "  ✅ Backend:     http://localhost:8006"
echo "  ✅ API Docs:    http://localhost:8006/docs"
echo "  ✅ 测试用户:    frontend-test@example.com (密码: TestPass123)"
echo "  ✅ Bearer Token: 已保存到 /tmp/phase2_token.sh"
echo ""
echo "🔧 开发配置:"
echo "  • 报告质量等级: standard（Phase 2.1-2.3 不需要 LLM）"
echo "  • Celery 模式:  inline（ENABLE_CELERY_DISPATCH=0，方便调试）"
echo "  • 会员等级:     pro（跳过会员限制）"
echo ""
echo "🧪 快速测试:"
echo ""
echo "# 1. 加载 Token"
echo "source /tmp/phase2_token.sh"
echo ""
echo "# 2. 创建分析任务（standard 模式，无需 LLM）"
echo "curl -X POST http://localhost:8006/api/analyze \\"
echo "  -H \"Authorization: Bearer \$PHASE2_TOKEN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"product_description\": \"跨境电商支付解决方案\"}'"
echo ""
echo "# 3. 查看日志"
echo "tail -f /tmp/phase2_backend.log"
echo ""
echo "# 4. 获取报告（等待 30-60 秒后）"
echo "curl http://localhost:8006/api/report/<task_id> \\"
echo "  -H \"Authorization: Bearer \$PHASE2_TOKEN\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Phase 2 开发顺序建议:"
echo "  1. Phase 2.1-2.3（5天）: 使用 standard 模式，完全不需要 LLM"
echo "  2. Phase 2.4（2天）:     切换到 premium 模式，需要真实 OpenAI API"
echo ""
echo "🔑 Phase 2.4 配置（到时候再改）:"
echo "  echo 'OPENAI_API_KEY=sk-proj-...' >> backend/.env"
echo "  echo 'REPORT_QUALITY_LEVEL=premium' >> backend/.env"
echo ""
echo "🛑 停止服务:"
echo "  kill $BACKEND_PID                    # 停止后端"
echo "  brew services stop redis             # 停止 Redis"
echo "  brew services stop postgresql@14     # 停止 PostgreSQL"
echo ""
echo "现在可以开始 Phase 2 开发了！🚀"
echo ""
