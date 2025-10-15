#!/bin/bash
# 服务状态检查脚本
# 检查前后端服务是否正常运行

set -e

BACKEND_PORT=8006
FRONTEND_PORT=3006
BACKEND_URL="http://localhost:${BACKEND_PORT}"
FRONTEND_URL="http://localhost:${FRONTEND_PORT}"

echo "🔍 检查服务状态..."
echo ""

# 检查后端
echo "1️⃣  检查后端服务 (端口 ${BACKEND_PORT})..."
if lsof -ti:${BACKEND_PORT} > /dev/null 2>&1; then
    echo "   ✅ 后端端口 ${BACKEND_PORT} 正在使用"
    
    # 检查 API 是否响应
    if curl -s "${BACKEND_URL}/openapi.json" > /dev/null 2>&1; then
        API_INFO=$(curl -s "${BACKEND_URL}/openapi.json" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"{data['info']['title']} v{data['info']['version']}\")" 2>/dev/null || echo "Unknown")
        echo "   ✅ 后端 API 正常响应: ${API_INFO}"
        echo "   📖 API 文档: ${BACKEND_URL}/docs"
    else
        echo "   ⚠️  后端端口已占用但 API 未响应"
    fi
else
    echo "   ❌ 后端未运行"
    echo "   💡 启动命令: make dev-backend"
fi

echo ""

# 检查前端
echo "2️⃣  检查前端服务 (端口 ${FRONTEND_PORT})..."
if lsof -ti:${FRONTEND_PORT} > /dev/null 2>&1; then
    echo "   ✅ 前端端口 ${FRONTEND_PORT} 正在使用"
    
    # 检查前端是否响应
    if curl -s "${FRONTEND_URL}/" > /dev/null 2>&1; then
        echo "   ✅ 前端服务正常响应"
        echo "   🌐 访问地址: ${FRONTEND_URL}"
    else
        echo "   ⚠️  前端端口已占用但服务未响应"
    fi
else
    echo "   ❌ 前端未运行"
    echo "   💡 启动命令: make dev-frontend"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 总结
BACKEND_RUNNING=$(lsof -ti:${BACKEND_PORT} > /dev/null 2>&1 && echo "1" || echo "0")
FRONTEND_RUNNING=$(lsof -ti:${FRONTEND_PORT} > /dev/null 2>&1 && echo "1" || echo "0")

if [ "$BACKEND_RUNNING" = "1" ] && [ "$FRONTEND_RUNNING" = "1" ]; then
    echo "✅ 所有服务正常运行"
    echo ""
    echo "🚀 快速访问:"
    echo "   前端: ${FRONTEND_URL}"
    echo "   后端: ${BACKEND_URL}/docs"
elif [ "$BACKEND_RUNNING" = "0" ] && [ "$FRONTEND_RUNNING" = "0" ]; then
    echo "❌ 所有服务未运行"
    echo ""
    echo "💡 启动所有服务:"
    echo "   终端 1: make dev-backend"
    echo "   终端 2: make dev-frontend"
    echo ""
    echo "或使用重启命令:"
    echo "   make restart-backend  # 在终端 1"
    echo "   make restart-frontend # 在终端 2"
else
    echo "⚠️  部分服务未运行"
    echo ""
    if [ "$BACKEND_RUNNING" = "0" ]; then
        echo "💡 启动后端: make dev-backend"
    fi
    if [ "$FRONTEND_RUNNING" = "0" ]; then
        echo "💡 启动前端: make dev-frontend"
    fi
fi

echo ""

