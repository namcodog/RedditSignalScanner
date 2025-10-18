#!/bin/bash
#
# Setup crontab for Celery auto-restart
# This script configures cron to:
# 1. Start Celery services on reboot
# 2. Check health every 5 minutes and restart if needed

set -euo pipefail

REPO_ROOT="/Users/hujia/Desktop/RedditSignalScanner"
START_SCRIPT="$REPO_ROOT/scripts/start_celery_services.sh"
HEALTH_SCRIPT="$REPO_ROOT/scripts/celery_health_check.sh"
LOG_DIR="$HOME/Library/Logs/reddit-scanner"
CRON_LOG="$LOG_DIR/cron.log"

echo "=========================================="
echo "🔧 配置 Crontab 自动重启"
echo "=========================================="
echo ""

# Make scripts executable
chmod +x "$START_SCRIPT"
chmod +x "$HEALTH_SCRIPT"
echo "✅ 脚本权限已设置"
echo ""

# Create log directory
mkdir -p "$LOG_DIR"
echo "✅ 日志目录已创建: $LOG_DIR"
echo ""

# Backup existing crontab
echo "📋 备份现有 crontab..."
crontab -l > "$LOG_DIR/crontab.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
echo "✅ 备份完成"
echo ""

# Create new crontab entries
echo "📝 创建新的 crontab 配置..."

# Get existing crontab (if any)
EXISTING_CRON=$(crontab -l 2>/dev/null || echo "")

# Remove old reddit-scanner entries
CLEANED_CRON=$(echo "$EXISTING_CRON" | grep -v "reddit-scanner\|celery_health_check\|start_celery_services" || true)

# Add new entries
NEW_CRON="$CLEANED_CRON

# Reddit Signal Scanner - Celery Auto-Restart
# Start Celery services on reboot (wait 30 seconds for system to stabilize)
@reboot sleep 30 && $START_SCRIPT >> $CRON_LOG 2>&1

# Health check every 5 minutes, restart if needed
*/5 * * * * $HEALTH_SCRIPT --all >> $CRON_LOG 2>&1 || $START_SCRIPT >> $CRON_LOG 2>&1
"

# Install new crontab
echo "$NEW_CRON" | crontab -

echo "✅ Crontab 配置完成"
echo ""

# Show installed crontab
echo "📋 当前 crontab 配置:"
echo "=========================================="
crontab -l | grep -A 5 "Reddit Signal Scanner" || crontab -l
echo "=========================================="
echo ""

echo "🎉 配置完成！"
echo ""
echo "📊 配置摘要:"
echo "  ✅ 开机自启: 系统重启后 30 秒自动启动 Celery"
echo "  ✅ 健康检查: 每 5 分钟检查一次，失败时自动重启"
echo "  ✅ 日志记录: $CRON_LOG"
echo ""
echo "📝 验证命令:"
echo "  查看 crontab: crontab -l"
echo "  查看日志: tail -f $CRON_LOG"
echo "  手动启动: bash $START_SCRIPT"
echo "  健康检查: bash $HEALTH_SCRIPT --all"
echo ""
echo "⚠️  注意事项:"
echo "  1. cron 任务会在后台自动运行"
echo "  2. 如需停止服务，请手动 kill 进程: pkill -f celery"
echo "  3. 如需移除 cron 任务: crontab -e (删除相关行)"
echo ""

