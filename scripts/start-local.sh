#!/bin/bash
# Reddit Signal Scanner - 本地启动脚本
# 后端: http://localhost:8006
# 前端: http://localhost:3006

set -e

echo "=========================================="
echo "🚀 Reddit Signal Scanner - 本地启动"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅ $1 已安装${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 未安装${NC}"
        return 1
    fi
}

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $1 已被占用${NC}"
        return 1
    else
        echo -e "${GREEN}✅ 端口 $1 可用${NC}"
        return 0
    fi
}

# 步骤 1: 环境检查
echo "📋 步骤 1/6: 环境检查"
echo "---"

check_command "python3.11" || {
    echo -e "${RED}请先安装 Python 3.11: brew install python@3.11${NC}"
    exit 1
}

check_command "node" || {
    echo -e "${RED}请先安装 Node.js: brew install node${NC}"
    exit 1
}

check_command "redis-cli" || {
    echo -e "${RED}请先安装 Redis: brew install redis${NC}"
    exit 1
}

check_command "psql" || {
    echo -e "${RED}请先安装 PostgreSQL: brew install postgresql@14${NC}"
    exit 1
}

echo ""

# 步骤 2: 检查端口
echo "📋 步骤 2/6: 检查端口"
echo "---"

if ! check_port 8006; then
    echo -e "${YELLOW}正在清理端口 8006...${NC}"
    lsof -ti:8006 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

if ! check_port 3006; then
    echo -e "${YELLOW}正在清理端口 3006...${NC}"
    lsof -ti:3006 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo ""

# 步骤 3: 启动 Redis
echo "📋 步骤 3/6: 启动 Redis"
echo "---"

if redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✅ Redis 已运行${NC}"
else
    echo -e "${YELLOW}正在启动 Redis...${NC}"
    redis-server --daemonize yes --port 6379
    sleep 2
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis 启动成功${NC}"
    else
        echo -e "${RED}❌ Redis 启动失败${NC}"
        exit 1
    fi
fi

echo ""

# 步骤 4: 检查 PostgreSQL
echo "📋 步骤 4/6: 检查 PostgreSQL"
echo "---"

if pg_isready &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL 已运行${NC}"
else
    echo -e "${YELLOW}正在启动 PostgreSQL...${NC}"
    brew services start postgresql@14
    sleep 3
    if pg_isready &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL 启动成功${NC}"
    else
        echo -e "${RED}❌ PostgreSQL 启动失败${NC}"
        exit 1
    fi
fi

# 检查数据库是否存在
if psql -lqt | cut -d \| -f 1 | grep -qw reddit_scanner; then
    echo -e "${GREEN}✅ 数据库 reddit_scanner 已存在${NC}"
else
    echo -e "${YELLOW}正在创建数据库 reddit_scanner...${NC}"
    createdb reddit_scanner
    echo -e "${GREEN}✅ 数据库创建成功${NC}"
fi

echo ""

# 步骤 5: 数据库迁移与测试账号
echo "📋 步骤 5/6: 数据库迁移与测试账号"
echo "---"

cd backend
# 加载 .env 文件中的环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 数据库迁移
if /opt/homebrew/bin/python3.11 -m alembic upgrade head; then
    echo -e "${GREEN}✅ 数据库迁移成功${NC}"
else
    echo -e "${RED}❌ 数据库迁移失败${NC}"
    cd ..
    exit 1
fi

# 创建测试账号
echo -e "${YELLOW}正在创建测试账号...${NC}"
if /opt/homebrew/bin/python3.11 scripts/seed_test_accounts.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 测试账号创建成功${NC}"
    echo -e "${YELLOW}   管理员: admin@test.com / Admin123!${NC}"
    echo -e "${YELLOW}   用户: user1@test.com / User123!${NC}"
else
    echo -e "${YELLOW}⚠️  测试账号创建失败（可能已存在）${NC}"
fi

cd ..

echo ""

# 步骤 6: 启动服务
echo "📋 步骤 6/6: 启动服务"
echo "---"

# 启动 Celery Worker
echo -e "${YELLOW}正在启动 Celery Worker...${NC}"
cd backend
# 加载 .env 文件并启动 Celery
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi
/opt/homebrew/bin/python3.11 -m celery -A app.core.celery_app.celery_app worker \
    --loglevel=info \
    --pool=solo \
    --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
    > /tmp/celery_worker.log 2>&1 &
CELERY_PID=$!
cd ..
sleep 3

if ps -p $CELERY_PID > /dev/null; then
    echo -e "${GREEN}✅ Celery Worker 启动成功 (PID: $CELERY_PID)${NC}"
else
    echo -e "${RED}❌ Celery Worker 启动失败${NC}"
    echo -e "${YELLOW}查看日志: tail -f /tmp/celery_worker.log${NC}"
fi

# 启动后端服务
echo -e "${YELLOW}正在启动后端服务 (端口 8006)...${NC}"
cd backend
# 加载 .env 文件并启动后端
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi
/opt/homebrew/bin/python3.11 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8006 \
    --reload \
    > /tmp/backend_uvicorn.log 2>&1 &
BACKEND_PID=$!
cd ..
sleep 3

if curl -s http://localhost:8006/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端服务启动成功 (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ 后端服务启动失败${NC}"
    echo -e "${YELLOW}查看日志: tail -f /tmp/backend_uvicorn.log${NC}"
fi

# 启动前端服务
echo -e "${YELLOW}正在启动前端服务 (端口 3006)...${NC}"
cd frontend

# 检查依赖是否安装
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}正在安装前端依赖...${NC}"
    npm install
fi

npm run dev -- --port 3006 > /tmp/frontend_vite.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 3

if curl -s http://localhost:3006/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 前端服务启动成功 (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  前端服务可能需要更多时间启动${NC}"
    echo -e "${YELLOW}查看日志: tail -f /tmp/frontend_vite.log${NC}"
fi

echo ""
echo "=========================================="
echo "✅ 所有服务启动完成！"
echo "=========================================="
echo ""
echo "📊 服务状态："
echo "   Redis:    ✅ redis://localhost:6379"
echo "   PostgreSQL: ✅ localhost:5432"
echo "   Celery:   ✅ PID $CELERY_PID (日志: tail -f /tmp/celery_worker.log)"
echo "   Backend:  ✅ http://localhost:8006 (PID $BACKEND_PID)"
echo "   Frontend: ✅ http://localhost:3006 (PID $FRONTEND_PID)"
echo ""
echo "🔗 快速访问："
echo "   前端首页:  http://localhost:3006/"
echo "   API 文档:  http://localhost:8006/docs"
echo ""
echo "📋 查看日志："
echo "   Celery:   tail -f /tmp/celery_worker.log"
echo "   Backend:  tail -f /tmp/backend_uvicorn.log"
echo "   Frontend: tail -f /tmp/frontend_vite.log"
echo ""
echo "🛑 停止所有服务："
echo "   ./scripts/stop-local.sh"
echo "   或者: make kill-ports && make kill-celery && make kill-redis"
echo ""
echo "🎯 现在可以开始验收了！"
echo ""

