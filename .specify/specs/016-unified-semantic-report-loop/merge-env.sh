#!/bin/bash
# 智能合并 Phase 2 配置到 backend/.env
# 保留现有配置（如 Reddit API keys），只添加缺失的 Phase 2 配置
# 兼容 macOS 自带 bash 3.2（不使用关联数组）

set -e

ENVFILE="backend/.env"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🔧 智能合并 Phase 2 配置到 backend/.env"
echo ""

# ============================================
# 1. 检查现有配置文件
# ============================================
if [ ! -f "$ENVFILE" ]; then
    echo "❌ 未找到 $ENVFILE"
    echo "   请先创建配置文件，或运行："
    echo "   cp backend/.env.example backend/.env"
    exit 1
fi

echo "✅ 检测到现有配置文件：$ENVFILE"
echo ""

# ============================================
# 2. 备份现有配置
# ============================================
BACKUP_FILE="${ENVFILE}.backup_${TIMESTAMP}"
cp "$ENVFILE" "$BACKUP_FILE"
echo "✅ 已备份到：$BACKUP_FILE"
echo ""

# ============================================
# 3. 定义需要添加的 Phase 2 配置（兼容 bash 3.2）
# ============================================
# 格式：key|value
PHASE2_CONFIGS=(
    "REPORT_QUALITY_LEVEL|standard"
    "ENABLE_CELERY_DISPATCH|0"
    "DEFAULT_MEMBERSHIP_LEVEL|pro"
    "APP_ENV|development"
    "CELERY_BROKER_URL|redis://localhost:6379/1"
    "CELERY_RESULT_BACKEND|redis://localhost:6379/2"
    "TASK_STATUS_REDIS_URL|redis://localhost:6379/3"
    "REPORT_CACHE_TTL_SECONDS|3600"
    "REPORT_RATE_LIMIT_PER_MINUTE|30"
)

# ============================================
# 4. 检查并添加缺失配置
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 检查并添加缺失的 Phase 2 配置..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ADDED_COUNT=0
SKIPPED_COUNT=0

for item in "${PHASE2_CONFIGS[@]}"; do
    key="${item%%|*}"
    value="${item#*|}"

    # 检查配置是否已存在
    if grep -q "^${key}=" "$ENVFILE"; then
        echo "⏭️  跳过（已存在）：$key"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    else
        # 添加配置
        echo "${key}=${value}" >> "$ENVFILE"
        echo "✅ 已添加：$key=$value"
        ADDED_COUNT=$((ADDED_COUNT + 1))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 合并结果："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 新增配置：$ADDED_COUNT 项"
echo "  ⏭️  跳过配置：$SKIPPED_COUNT 项"
echo "  💾 备份文件：$BACKUP_FILE"
echo ""

# ============================================
# 5. 验证关键配置
# ============================================
echo "🔍 验证关键配置..."
echo ""

MISSING_KEYS=""

for key in "DATABASE_URL" "REDIS_URL" "JWT_SECRET"; do
    if ! grep -q "^${key}=" "$ENVFILE"; then
        MISSING_KEYS="${MISSING_KEYS}   - $key\n"
    fi
done

if [ -n "$MISSING_KEYS" ]; then
    echo "⚠️  警告：以下关键配置缺失，请手动添加："
    echo -e "$MISSING_KEYS"
    echo ""
fi

# ============================================
# 6. 显示最终配置
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 最终配置预览（前 20 行）："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
head -20 "$ENVFILE"
echo "..."
echo ""

echo "✅ 配置合并完成！"
echo ""
echo "🚀 下一步："
echo "   1. 检查配置：cat $ENVFILE"
echo "   2. 启动后端：make dev-backend"
echo "   3. 如有问题，恢复备份：cp $BACKUP_FILE $ENVFILE"
echo ""
