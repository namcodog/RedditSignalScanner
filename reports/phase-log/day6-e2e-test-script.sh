#!/bin/bash
# Day 6 端到端测试脚本
# 验证完整的用户流程：注册 → 创建任务 → 查询状态 → 获取报告

set -e  # 遇到错误立即退出

echo "========================================="
echo "Day 6 端到端测试"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_step() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${YELLOW}[Test $TOTAL_TESTS]${NC} $1"
}

test_pass() {
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ PASS${NC} $1"
    echo ""
}

test_fail() {
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ FAIL${NC} $1"
    echo ""
}

# 步骤 1: 注册用户
test_step "用户注册"
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8006/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"e2e-test-$(date +%s)@example.com\",\"password\":\"TestPass123!\"}")

TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.access_token')
USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.user.id')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    test_pass "用户注册成功，获得 Token"
    echo "   User ID: $USER_ID"
    echo "   Token: ${TOKEN:0:50}..."
else
    test_fail "用户注册失败"
    echo "   Response: $REGISTER_RESPONSE"
    exit 1
fi

# 步骤 2: 创建分析任务
test_step "创建分析任务"
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_description":"一款帮助忙碌专业人士进行餐食准备的移动应用"}')

TASK_ID=$(echo $CREATE_RESPONSE | jq -r '.task_id')
TASK_STATUS=$(echo $CREATE_RESPONSE | jq -r '.status')

if [ "$TASK_ID" != "null" ] && [ -n "$TASK_ID" ]; then
    test_pass "任务创建成功"
    echo "   Task ID: $TASK_ID"
    echo "   Status: $TASK_STATUS"
else
    test_fail "任务创建失败"
    echo "   Response: $CREATE_RESPONSE"
    exit 1
fi

# 步骤 3: 查询任务状态（立即查询）
test_step "查询任务状态（立即）"
STATUS_RESPONSE=$(curl -s http://localhost:8006/api/status/$TASK_ID \
  -H "Authorization: Bearer $TOKEN")

CURRENT_STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')

if [ "$CURRENT_STATUS" != "null" ]; then
    test_pass "任务状态查询成功"
    echo "   Status: $CURRENT_STATUS"
    echo "   Progress: $PROGRESS%"
else
    test_fail "任务状态查询失败"
    echo "   Response: $STATUS_RESPONSE"
    exit 1
fi

# 步骤 4: 等待任务完成（最多等待 30 秒）
test_step "等待任务完成（最多 30 秒）"
MAX_WAIT=30
WAIT_COUNT=0
TASK_COMPLETED=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    
    STATUS_RESPONSE=$(curl -s http://localhost:8006/api/status/$TASK_ID \
      -H "Authorization: Bearer $TOKEN")
    
    CURRENT_STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')
    
    echo -n "."
    
    if [ "$CURRENT_STATUS" = "completed" ]; then
        TASK_COMPLETED=true
        echo ""
        break
    fi
    
    if [ "$CURRENT_STATUS" = "failed" ]; then
        echo ""
        ERROR_MSG=$(echo $STATUS_RESPONSE | jq -r '.error')
        test_fail "任务执行失败"
        echo "   Error: $ERROR_MSG"
        exit 1
    fi
done

if [ "$TASK_COMPLETED" = true ]; then
    test_pass "任务在 $WAIT_COUNT 秒内完成"
    echo "   Final Status: $CURRENT_STATUS"
    echo "   Progress: $PROGRESS%"
else
    test_fail "任务在 $MAX_WAIT 秒内未完成"
    echo "   Current Status: $CURRENT_STATUS"
    echo "   Progress: $PROGRESS%"
fi

# 步骤 5: 获取分析报告
test_step "获取分析报告"
REPORT_RESPONSE=$(curl -s http://localhost:8006/api/report/$TASK_ID \
  -H "Authorization: Bearer $TOKEN")

REPORT_ID=$(echo $REPORT_RESPONSE | jq -r '.report_id')
SUBREDDIT_COUNT=$(echo $REPORT_RESPONSE | jq -r '.summary.total_subreddits')
POST_COUNT=$(echo $REPORT_RESPONSE | jq -r '.summary.total_posts')
INSIGHT_COUNT=$(echo $REPORT_RESPONSE | jq -r '.summary.total_insights')

if [ "$REPORT_ID" != "null" ] && [ -n "$REPORT_ID" ]; then
    test_pass "报告获取成功"
    echo "   Report ID: $REPORT_ID"
    echo "   Subreddits: $SUBREDDIT_COUNT"
    echo "   Posts: $POST_COUNT"
    echo "   Insights: $INSIGHT_COUNT"
else
    test_fail "报告获取失败"
    echo "   Response: $REPORT_RESPONSE"
fi

# 步骤 6: 验证报告内容
test_step "验证报告内容完整性"
HAS_INSIGHTS=$(echo $REPORT_RESPONSE | jq -r '.insights | length')
HAS_OPPORTUNITIES=$(echo $REPORT_RESPONSE | jq -r '.opportunities | length')
HAS_PAIN_POINTS=$(echo $REPORT_RESPONSE | jq -r '.pain_points | length')

if [ "$HAS_INSIGHTS" -gt 0 ] && [ "$HAS_OPPORTUNITIES" -gt 0 ] && [ "$HAS_PAIN_POINTS" -gt 0 ]; then
    test_pass "报告内容完整"
    echo "   Insights: $HAS_INSIGHTS 条"
    echo "   Opportunities: $HAS_OPPORTUNITIES 条"
    echo "   Pain Points: $HAS_PAIN_POINTS 条"
else
    test_fail "报告内容不完整"
    echo "   Insights: $HAS_INSIGHTS"
    echo "   Opportunities: $HAS_OPPORTUNITIES"
    echo "   Pain Points: $HAS_PAIN_POINTS"
fi

# 测试总结
echo ""
echo "========================================="
echo "测试总结"
echo "========================================="
echo -e "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}❌ 有测试失败！${NC}"
    exit 1
fi

