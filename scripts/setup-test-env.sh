#!/bin/bash
# 本地测试环境前置准备脚本
# 用途：配置 Reddit API 凭证、创建测试数据、验证环境

set -e  # 遇到错误立即退出

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   本地测试环境前置准备                                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ============================================================
# Task 0.1: 检查 Reddit API 凭证
# ============================================================

echo "📋 Task 0.1: 检查 Reddit API 凭证"
echo "----------------------------------------"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到 .env 文件，创建模板...${NC}"
    cat > .env <<EOF
# Reddit API 凭证（从 https://www.reddit.com/prefs/apps 获取）
REDDIT_CLIENT_ID=your_actual_client_id
REDDIT_CLIENT_SECRET=your_actual_client_secret
REDDIT_USER_AGENT=RedditSignalScanner/Test:v1.0
EOF
    echo -e "${RED}❌ 请编辑 .env 文件，填入真实的 Reddit API 凭证${NC}"
    echo ""
    echo "获取凭证步骤："
    echo "1. 访问 https://www.reddit.com/prefs/apps"
    echo "2. 点击 'Create App' 或 'Create Another App'"
    echo "3. 选择 'script' 类型"
    echo "4. 填写名称和描述"
    echo "5. 复制 client_id 和 client_secret 到 .env 文件"
    echo ""
    exit 1
fi

# 加载环境变量
export $(cat .env | grep REDDIT | xargs)

# 验证凭证
if [ -z "$REDDIT_CLIENT_ID" ] || [ "$REDDIT_CLIENT_ID" = "your_actual_client_id" ]; then
    echo -e "${RED}❌ REDDIT_CLIENT_ID 未配置或使用默认值${NC}"
    echo "请编辑 .env 文件，填入真实凭证"
    exit 1
fi

if [ -z "$REDDIT_CLIENT_SECRET" ] || [ "$REDDIT_CLIENT_SECRET" = "your_actual_client_secret" ]; then
    echo -e "${RED}❌ REDDIT_CLIENT_SECRET 未配置或使用默认值${NC}"
    echo "请编辑 .env 文件，填入真实凭证"
    exit 1
fi

echo -e "${GREEN}✅ Reddit API 凭证已配置${NC}"
echo "   Client ID: ${REDDIT_CLIENT_ID:0:10}..."
echo "   Client Secret: ${REDDIT_CLIENT_SECRET:0:10}..."
echo ""

# ============================================================
# Task 0.2: 创建测试数据文件
# ============================================================

echo "📋 Task 0.2: 创建测试数据文件"
echo "----------------------------------------"

mkdir -p backend/data

cat > backend/data/test_seed_communities.json <<EOF
{
  "high_priority": ["r/artificial", "r/startups", "r/entrepreneur"],
  "medium_priority": ["r/saas", "r/ProductManagement"],
  "low_priority": ["r/technology", "r/programming", "r/webdev", "r/datascience", "r/machinelearning"]
}
EOF

echo -e "${GREEN}✅ 测试数据文件已创建${NC}"
echo "   文件: backend/data/test_seed_communities.json"
echo "   社区数量: 10 个（减少 API 调用）"
echo ""

# 验证 JSON 格式
if command -v jq &> /dev/null; then
    cat backend/data/test_seed_communities.json | jq '.' > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ JSON 格式验证通过${NC}"
    else
        echo -e "${RED}❌ JSON 格式错误${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  未安装 jq，跳过 JSON 格式验证${NC}"
fi
echo ""

# ============================================================
# Task 0.3: 验证 Docker 环境
# ============================================================

echo "📋 Task 0.3: 验证 Docker 环境"
echo "----------------------------------------"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    echo "请访问 https://www.docker.com/get-started 安装 Docker"
    exit 1
fi

echo -e "${GREEN}✅ Docker 已安装${NC}"
docker --version

# 检查 Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    echo "请安装 Docker Compose v2"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose 已安装${NC}"
docker compose version
echo ""

# 检查 Docker 服务
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker 服务未运行${NC}"
    echo "请启动 Docker Desktop 或 Docker 守护进程"
    exit 1
fi

echo -e "${GREEN}✅ Docker 服务运行中${NC}"
echo ""

# ============================================================
# Task 0.4: 验证端口可用性
# ============================================================

echo "📋 Task 0.4: 验证端口可用性"
echo "----------------------------------------"

check_port() {
    local port=$1
    local service=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $port ($service) 已被占用${NC}"
        echo "   占用进程:"
        lsof -i :$port | grep LISTEN
        return 1
    else
        echo -e "${GREEN}✅ 端口 $port ($service) 可用${NC}"
        return 0
    fi
}

check_port 18000 "FastAPI 测试服务器"
check_port 15432 "PostgreSQL 测试数据库"
check_port 16379 "Redis 测试缓存"
echo ""

# ============================================================
# Task 0.5: 验证 Docker Compose 配置
# ============================================================

echo "📋 Task 0.5: 验证 Docker Compose 配置"
echo "----------------------------------------"

if [ ! -f "docker-compose.test.yml" ]; then
    echo -e "${RED}❌ docker-compose.test.yml 文件不存在${NC}"
    exit 1
fi

# 验证配置文件语法
docker compose -f docker-compose.test.yml config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker Compose 配置文件语法正确${NC}"
else
    echo -e "${RED}❌ Docker Compose 配置文件语法错误${NC}"
    docker compose -f docker-compose.test.yml config
    exit 1
fi
echo ""

# ============================================================
# 总结
# ============================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   ✅ 前置准备完成！                                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 环境检查结果:"
echo "   ✅ Reddit API 凭证已配置"
echo "   ✅ 测试数据文件已创建"
echo "   ✅ Docker 环境正常"
echo "   ✅ 端口可用"
echo "   ✅ Docker Compose 配置正确"
echo ""
echo "🚀 下一步:"
echo "   1. 启动测试环境:"
echo "      make test-env-up"
echo ""
echo "   2. 执行完整验收流程:"
echo "      make test-all-acceptance"
echo ""
echo "   3. 或分步执行:"
echo "      make test-stage-1  # 环境准备"
echo "      make test-stage-2  # 核心服务"
echo "      make test-stage-3  # API 端点"
echo "      make test-stage-4  # 任务调度"
echo "      make test-stage-5  # 端到端"
echo ""
echo "📚 详细文档:"
echo "   .specify/specs/002-local-acceptance-testing/README.md"
echo "   .specify/specs/002-local-acceptance-testing/tasks.md"
echo ""

