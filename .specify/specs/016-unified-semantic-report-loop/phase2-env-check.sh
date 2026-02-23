#!/bin/bash
# Phase 2 环境配置检查脚本（不覆盖现有配置）
# 兼容 macOS 自带 bash 3.2（不使用关联数组）

set -e

ENVFILE="backend/.env"

echo "🔍 Phase 2 环境配置检查"
echo ""

# ============================================
# 1. 检查配置文件是否存在
# ============================================
if [ ! -f "$ENVFILE" ]; then
    echo "❌ 未找到 $ENVFILE"
    echo ""
    echo "请先创建配置文件："
    echo "  cp backend/.env.example backend/.env"
    exit 1
fi

echo "✅ 找到配置文件：$ENVFILE"
echo ""

# ============================================
# 2. 定义 Phase 2 必需配置（兼容 bash 3.2）
# ============================================
# 格式：key|default_value
REQUIRED_CONFIGS=(
    "DATABASE_URL|postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner"
    "REDIS_URL|redis://localhost:6379/5"
    "JWT_SECRET|phase2-dev-secret"
    "REPORT_QUALITY_LEVEL|standard"
    "ENABLE_CELERY_DISPATCH|0"
    "DEFAULT_MEMBERSHIP_LEVEL|pro"
)

OPTIONAL_CONFIGS=(
    "CELERY_BROKER_URL|redis://localhost:6379/1"
    "CELERY_RESULT_BACKEND|redis://localhost:6379/2"
    "APP_ENV|development"
    "OPENAI_API_KEY|(Phase 2.4 需要)"
)

# ============================================
# 3. 检查必需配置
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 检查必需配置..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

MISSING_REQUIRED=""

for item in "${REQUIRED_CONFIGS[@]}"; do
    key="${item%%|*}"
    default_value="${item#*|}"

    if grep -q "^${key}=" "$ENVFILE" && ! grep -q "^${key}=$" "$ENVFILE" && ! grep -q "^${key}=\"\"$" "$ENVFILE"; then
        echo "✅ $key (已配置)"
    else
        echo "❌ $key (缺失或为空)"
        MISSING_REQUIRED="${MISSING_REQUIRED}${key}=${default_value}\n"
    fi
done

echo ""

# ============================================
# 4. 检查可选配置
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 检查可选配置..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for item in "${OPTIONAL_CONFIGS[@]}"; do
    key="${item%%|*}"
    hint="${item#*|}"

    if grep -q "^${key}=" "$ENVFILE" && ! grep -q "^${key}=$" "$ENVFILE" && ! grep -q "^${key}=\"\"$" "$ENVFILE"; then
        echo "✅ $key (已配置)"
    else
        echo "⚠️  $key (缺失) - $hint"
    fi
done

echo ""

# ============================================
# 5. 生成配置建议
# ============================================
if [ -n "$MISSING_REQUIRED" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔧 需要添加的配置："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "请将以下配置添加到 backend/.env："
    echo ""
    echo -e "$MISSING_REQUIRED"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🛠️  添加方式（3 选 1）："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1️⃣  手动添加（最安全）："
    echo "   编辑 backend/.env，复制上面的配置"
    echo ""
    echo "2️⃣  使用智能合并脚本："
    echo "   bash .specify/specs/016-unified-semantic-report-loop/merge-env.sh"
    echo ""
    echo "3️⃣  使用命令追加（快捷）："
    cat > /tmp/phase2_append_env.sh << 'APPEND_EOF'
#!/bin/bash
# 追加缺失配置到 backend/.env
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
cp backend/.env backend/.env.backup_$TIMESTAMP
echo "✅ 已备份到 backend/.env.backup_$TIMESTAMP"
APPEND_EOF

    # 生成追加命令
    echo -e "$MISSING_REQUIRED" | while IFS= read -r line; do
        if [ -n "$line" ]; then
            echo "echo '$line' >> backend/.env" >> /tmp/phase2_append_env.sh
        fi
    done

    echo "echo '✅ 配置已追加' >> /tmp/phase2_append_env.sh"
    chmod +x /tmp/phase2_append_env.sh

    echo "   bash /tmp/phase2_append_env.sh"
    echo ""

    exit 1
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 所有必需配置已就绪！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "✅ Phase 2 环境配置检查通过"
    echo ""
    echo "🚀 下一步："
    echo "   1. 启动后端：make dev-backend"
    echo "   2. 创建测试用户：python backend/scripts/create_test_users.py"
    echo "   3. 生成 Token：见 QUICKSTART.md"
    echo ""
fi
