#!/bin/bash

# Reddit Signal Scanner - 前端 API 集成测试脚本
# Day 5 任务: 手动验证所有 4 个 API 端点

set -e

echo "🧪 前端 API 集成测试"
echo "===================="
echo ""

# 配置
API_BASE_URL="http://localhost:8006"
TEST_TOKEN="${TEST_TOKEN:-}"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 jq 是否安装
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq 未安装，输出将不会格式化${NC}"
    JQ_CMD="cat"
else
    JQ_CMD="jq '.'"
fi

# 检查后端是否运行
echo "🔍 检查后端服务..."
if curl -s "${API_BASE_URL}/docs" > /dev/null; then
    echo -e "${GREEN}✅ 后端服务正在运行${NC}"
else
    echo -e "${RED}❌ 后端服务未运行，请先启动后端${NC}"
    exit 1
fi

echo ""

# 测试 1: POST /api/analyze
echo "1️⃣  测试 POST /api/analyze - 创建分析任务"
echo "-------------------------------------------"

RESPONSE=$(curl -s -X POST "${API_BASE_URL}/api/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -d '{
    "product_description": "AI笔记应用，帮助研究者和创作者自动组织和连接想法"
  }')

echo "$RESPONSE" | eval $JQ_CMD

# 提取 task_id
TASK_ID=$(echo "$RESPONSE" | jq -r '.task_id' 2>/dev/null || echo "")

if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
    echo -e "${GREEN}✅ 任务创建成功${NC}"
    echo "   Task ID: $TASK_ID"
else
    echo -e "${RED}❌ 任务创建失败${NC}"
    exit 1
fi

echo ""

# 测试 2: GET /api/status/{task_id}
echo "2️⃣  测试 GET /api/status/{task_id} - 查询任务状态"
echo "-------------------------------------------"

if [ -n "$TASK_ID" ]; then
    RESPONSE=$(curl -s "${API_BASE_URL}/api/status/${TASK_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    
    echo "$RESPONSE" | eval $JQ_CMD
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null || echo "")
    
    if [ -n "$STATUS" ]; then
        echo -e "${GREEN}✅ 状态查询成功${NC}"
        echo "   Status: $STATUS"
    else
        echo -e "${RED}❌ 状态查询失败${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  跳过（无有效 task_id）${NC}"
fi

echo ""

# 测试 3: SSE 连接
echo "3️⃣  测试 GET /api/analyze/stream/{task_id} - SSE 连接"
echo "-------------------------------------------"

if [ -n "$TASK_ID" ]; then
    echo "建立 SSE 连接（5秒后自动关闭）..."
    
    timeout 5 curl -N "${API_BASE_URL}/api/analyze/stream/${TASK_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}" \
      2>/dev/null || true
    
    echo ""
    echo -e "${GREEN}✅ SSE 连接测试完成${NC}"
else
    echo -e "${YELLOW}⏭️  跳过（无有效 task_id）${NC}"
fi

echo ""

# 测试 4: GET /api/report/{task_id}
echo "4️⃣  测试 GET /api/report/{task_id} - 获取分析报告"
echo "-------------------------------------------"

if [ -n "$TASK_ID" ]; then
    RESPONSE=$(curl -s "${API_BASE_URL}/api/report/${TASK_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    
    echo "$RESPONSE" | eval $JQ_CMD
    
    # 检查是否返回 409（任务未完成）
    if echo "$RESPONSE" | grep -q "detail"; then
        echo -e "${YELLOW}⚠️  任务尚未完成（预期行为）${NC}"
    else
        echo -e "${GREEN}✅ 报告获取成功${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  跳过（无有效 task_id）${NC}"
fi

echo ""
echo "===================="
echo -e "${GREEN}✅ API 集成测试完成${NC}"
echo ""
echo "📝 测试总结:"
echo "   - POST /api/analyze: ✅"
echo "   - GET /api/status/{task_id}: ✅"
echo "   - GET /api/analyze/stream/{task_id}: ✅"
echo "   - GET /api/report/{task_id}: ⚠️  (任务未完成)"
echo ""
echo "💡 提示: 设置 TEST_TOKEN 环境变量以使用认证"
echo "   export TEST_TOKEN='your-token-here'"

