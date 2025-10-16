#!/bin/bash
# Reddit Signal Scanner - 停止本地服务脚本

set -e

echo "=========================================="
echo "🛑 Reddit Signal Scanner - 停止服务"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 停止端口 8006（后端）
echo "🛑 停止后端服务 (端口 8006)..."
if lsof -ti:8006 | xargs kill -9 2>/dev/null; then
    echo -e "${GREEN}✅ 后端服务已停止${NC}"
else
    echo -e "${YELLOW}⚠️  端口 8006 未被占用${NC}"
fi

# 停止端口 3006（前端）
echo "🛑 停止前端服务 (端口 3006)..."
if lsof -ti:3006 | xargs kill -9 2>/dev/null; then
    echo -e "${GREEN}✅ 前端服务已停止${NC}"
else
    echo -e "${YELLOW}⚠️  端口 3006 未被占用${NC}"
fi

# 停止 Celery Worker
echo "🛑 停止 Celery Worker..."
if pkill -f "celery.*worker" 2>/dev/null; then
    echo -e "${GREEN}✅ Celery Worker 已停止${NC}"
else
    echo -e "${YELLOW}⚠️  Celery Worker 未运行${NC}"
fi

# 停止 Redis（可选）
echo "🛑 停止 Redis..."
if redis-cli shutdown 2>/dev/null; then
    echo -e "${GREEN}✅ Redis 已停止${NC}"
else
    echo -e "${YELLOW}⚠️  Redis 未运行或无法停止${NC}"
fi

# 清理日志文件（可选）
echo "🧹 清理日志文件..."
rm -f /tmp/celery_worker.log
rm -f /tmp/backend_uvicorn.log
rm -f /tmp/frontend_vite.log
echo -e "${GREEN}✅ 日志文件已清理${NC}"

echo ""
echo "=========================================="
echo "✅ 所有服务已停止！"
echo "=========================================="
echo ""

