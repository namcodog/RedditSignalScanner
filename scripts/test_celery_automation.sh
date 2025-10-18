#!/bin/bash
#
# Test script for Celery automation setup
# Tests health check, supervisor, and launchd integration

set -euo pipefail

REPO_ROOT="/Users/hujia/Desktop/RedditSignalScanner"
HEALTH_SCRIPT="$REPO_ROOT/scripts/celery_health_check.sh"
SUPERVISOR_SCRIPT="$REPO_ROOT/scripts/celery_launchd_supervisor.sh"
PLIST_FILE="$HOME/Library/LaunchAgents/com.reddit.scanner.celery.plist"
LOG_DIR="$HOME/Library/Logs/reddit-scanner"

echo "=========================================="
echo "🧪 Celery 自动化测试"
echo "=========================================="
echo ""

# Step 1: Stop existing Celery processes
echo "📍 步骤 1: 停止现有 Celery 进程"
pkill -f "celery.*worker" 2>/dev/null || true
pkill -f "celery.*beat" 2>/dev/null || true
sleep 2

if pgrep -fl "celery" >/dev/null 2>&1; then
    echo "❌ 仍有 Celery 进程在运行:"
    pgrep -fl "celery"
    exit 1
else
    echo "✅ 所有 Celery 进程已停止"
fi
echo ""

# Step 2: Test health check script
echo "📍 步骤 2: 测试健康检查脚本"
chmod +x "$HEALTH_SCRIPT"

if "$HEALTH_SCRIPT" --worker 2>/dev/null; then
    echo "❌ Worker 应该不在运行"
    exit 1
else
    echo "✅ Worker 健康检查正确返回失败"
fi

if "$HEALTH_SCRIPT" --beat 2>/dev/null; then
    echo "❌ Beat 应该不在运行"
    exit 1
else
    echo "✅ Beat 健康检查正确返回失败"
fi
echo ""

# Step 3: Check plist file
echo "📍 步骤 3: 检查 LaunchAgent plist 文件"
if [[ -f "$PLIST_FILE" ]]; then
    echo "✅ plist 文件存在: $PLIST_FILE"
    
    # Validate plist
    if plutil -lint "$PLIST_FILE" >/dev/null 2>&1; then
        echo "✅ plist 文件格式正确"
    else
        echo "❌ plist 文件格式错误"
        plutil -lint "$PLIST_FILE"
        exit 1
    fi
else
    echo "❌ plist 文件不存在: $PLIST_FILE"
    exit 1
fi
echo ""

# Step 4: Check log directory
echo "📍 步骤 4: 检查日志目录"
if [[ -d "$LOG_DIR" ]]; then
    echo "✅ 日志目录存在: $LOG_DIR"
else
    echo "⚠️  日志目录不存在，将被创建: $LOG_DIR"
    mkdir -p "$LOG_DIR"
fi
echo ""

# Step 5: Load LaunchAgent
echo "📍 步骤 5: 加载 LaunchAgent"
launchctl unload -w "$PLIST_FILE" 2>/dev/null || true
sleep 1
launchctl load -w "$PLIST_FILE"
sleep 3
echo "✅ LaunchAgent 已加载"
echo ""

# Step 6: Verify LaunchAgent is running
echo "📍 步骤 6: 验证 LaunchAgent 运行状态"
if launchctl list | grep -q "com.reddit.scanner.celery"; then
    echo "✅ LaunchAgent 正在运行"
    launchctl list | grep "com.reddit.scanner.celery"
else
    echo "❌ LaunchAgent 未运行"
    exit 1
fi
echo ""

# Step 7: Wait for processes to start
echo "📍 步骤 7: 等待 Celery 进程启动 (最多 30 秒)"
for i in {1..30}; do
    if pgrep -fl "celery.*worker" >/dev/null 2>&1 && pgrep -fl "celery.*beat" >/dev/null 2>&1; then
        echo "✅ Celery Worker 和 Beat 已启动 (耗时 ${i} 秒)"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "❌ 超时：Celery 进程未在 30 秒内启动"
        echo "当前进程:"
        pgrep -fl "celery" || echo "无 Celery 进程"
        echo ""
        echo "Supervisor 日志:"
        tail -20 "$LOG_DIR/celery-supervisor.log" 2>/dev/null || echo "无日志"
        exit 1
    fi
    sleep 1
done
echo ""

# Step 8: Test health check with running processes
echo "📍 步骤 8: 测试健康检查（进程运行中）"
if "$HEALTH_SCRIPT" --worker; then
    echo "✅ Worker 健康检查通过"
else
    echo "❌ Worker 健康检查失败"
    exit 1
fi

if "$HEALTH_SCRIPT" --beat; then
    echo "✅ Beat 健康检查通过"
else
    echo "❌ Beat 健康检查失败"
    exit 1
fi

if "$HEALTH_SCRIPT" --all; then
    echo "✅ 全部健康检查通过"
else
    echo "❌ 全部健康检查失败"
    exit 1
fi
echo ""

# Step 9: Check process details
echo "📍 步骤 9: 检查进程详情"
echo "Worker 进程:"
pgrep -fl "celery.*worker"
echo ""
echo "Beat 进程:"
pgrep -fl "celery.*beat"
echo ""

# Step 10: Check logs
echo "📍 步骤 10: 检查日志文件"
for log_file in celery-worker.log celery-beat.log celery-supervisor.log; do
    log_path="$LOG_DIR/$log_file"
    if [[ -f "$log_path" ]]; then
        echo "✅ $log_file 存在 ($(wc -l < "$log_path") 行)"
    else
        echo "⚠️  $log_file 不存在"
    fi
done
echo ""

# Step 11: Test auto-restart (kill worker and wait for restart)
echo "📍 步骤 11: 测试自动重启机制"
echo "杀死 Worker 进程..."
pkill -f "celery.*worker"
sleep 5

if pgrep -fl "celery.*worker" >/dev/null 2>&1; then
    echo "✅ Worker 已自动重启"
else
    echo "❌ Worker 未自动重启"
    echo "Supervisor 日志:"
    tail -20 "$LOG_DIR/celery-supervisor.log"
    exit 1
fi
echo ""

# Step 12: Final verification
echo "📍 步骤 12: 最终验证"
echo "当前运行的 Celery 进程:"
pgrep -afl "celery"
echo ""

echo "=========================================="
echo "🎉 所有测试通过！"
echo "=========================================="
echo ""
echo "📊 测试摘要:"
echo "  ✅ 健康检查脚本正常工作"
echo "  ✅ LaunchAgent 配置正确"
echo "  ✅ Celery Worker 和 Beat 自动启动"
echo "  ✅ 自动重启机制正常工作"
echo "  ✅ 日志文件正常生成"
echo ""
echo "📝 下一步:"
echo "  1. 查看日志: tail -f $LOG_DIR/celery-supervisor.log"
echo "  2. 停止服务: launchctl unload -w $PLIST_FILE"
echo "  3. 启动服务: launchctl load -w $PLIST_FILE"
echo "  4. 检查状态: launchctl list | grep com.reddit.scanner.celery"
echo ""

