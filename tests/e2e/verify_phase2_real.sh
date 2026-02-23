#!/bin/bash
# tests/e2e/verify_phase2_real.sh
# 真实场景端到端验收脚本 (Phase 2)
# 验证：POST /analyze -> Polling -> Report (Markdown) -> Data Integrity

set -e

# --- 配置 ---
API_URL="http://localhost:8006/api"
PRODUCT_DESC="跨境电商支付解决方案"
# 确保不做 Mock，走真实逻辑
export FAST_E2E_REPORT=0
export ALLOW_MOCK_FALLBACK=0
export REPORT_QUALITY_LEVEL=${REPORT_QUALITY_LEVEL:-standard} # 默认 standard, 可被外部覆盖为 premium

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%T')] $1${NC}"; }
pass() { echo -e "${GREEN}✅ $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# --- 1. 环境准备 ---
log "1. 准备环境..."

# 获取 Token (复用之前的 Python 脚本)
log "获取 Access Token..."
REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TOKEN=$(python3 "$REPO_ROOT/scripts/get_dev_token.py" | tail -n 1)
if [ -z "$TOKEN" ] || [ ${#TOKEN} -lt 20 ]; then
    fail "Token 获取失败"
fi
log "Token 获取成功"

# --- 2. 提交分析任务 ---
log "2. 提交分析任务..."
RESPONSE=$(curl -s -X POST "$API_URL/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"product_description\": \"$PRODUCT_DESC\"}")

TASK_ID=$(echo $RESPONSE | grep -o '"task_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$TASK_ID" ] || [ "$TASK_ID" == "null" ]; then
    echo "Response: $RESPONSE"
    fail "任务提交失败"
fi
pass "任务提交成功: $TASK_ID"

# --- 3. 轮询等待任务完成 ---
log "3. 等待任务完成 (超时 300s)..."
MAX_RETRIES=60
for ((i=1; i<=MAX_RETRIES; i++)); do
    STATUS_RES=$(curl -s -X GET "$API_URL/tasks/$TASK_ID" -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo $STATUS_RES | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    if [ "$STATUS" == "completed" ]; then
        pass "任务已完成"
        break
    elif [ "$STATUS" == "failed" ]; then
        fail "任务失败: $STATUS_RES"
    fi
    
    log "当前状态: $STATUS (等待 ${i}x5s)..."
    sleep 5
    
    if [ $i -eq $MAX_RETRIES ]; then
        fail "任务超时"
    fi
done

# --- 4. 获取并验证报告 ---
log "4. 下载报告..."
REPORT_MD="/tmp/report_$TASK_ID.md"
curl -s -X GET "$API_URL/report/$TASK_ID/download?format=md" \
    -H "Authorization: Bearer $TOKEN" > "$REPORT_MD"

if [ ! -s "$REPORT_MD" ]; then
    fail "报告文件为空"
fi
pass "报告下载成功: $REPORT_MD"

# --- 5. 深度验证内容 ---
log "5. 验证报告内容真实性..."

# 5.1 验证社区名 (排除 r/test, r/demo)
log "检查社区引用..."
COMMUNITIES=$(grep -o "r/[A-Za-z0-9_]\+" "$REPORT_MD" | sort | uniq | head -n 5)
echo "发现社区: "
echo "$COMMUNITIES"
if [[ "$COMMUNITIES" == *"r/amazon"* ]] || [[ "$COMMUNITIES" == *"r/shopify"* ]]; then
    pass "发现真实 T1 社区引用"
else
    fail "未发现典型的 T1 社区 (Amazon/Shopify)"
fi

# 5.2 验证数据源标记
log "检查数据源头..."
# 检查报告头部或 JSON response header
REPORT_JSON=$(curl -s -X GET "$API_URL/report/$TASK_ID" -H "Authorization: Bearer $TOKEN")
DATA_SOURCE=$(echo $REPORT_JSON | grep -o '"data_source":"[^"]*' | cut -d'"' -f4)

if [ "$DATA_SOURCE" == "real" ]; then
    pass "数据源确认: Real"
else
    fail "数据源异常: $DATA_SOURCE (预期 Real)"
fi

# 5.3 验证分析深度 (Insights)
log "检查分析深度..."
PAIN_COUNT=$(echo $REPORT_JSON | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('report', {}).get('pain_points', [])))")
if [ "$PAIN_COUNT" -gt 0 ]; then
    pass "提取到 $PAIN_COUNT 个痛点"
else
    fail "未提取到痛点"
fi

# 5.4 验证 LLM (如果开启)
if [ "$REPORT_QUALITY_LEVEL" == "premium" ]; then
    log "检查 LLM 痕迹..."
    # 检查是否包含 LLM 润色的特征，例如 "战场画像" 或更自然的语言
    if grep -q "用户画像" "$REPORT_MD"; then
        pass "发现 LLM 生成的内容特征 (用户画像)"
    else
        echo "⚠️ 警告: 未发现明显的 LLM 生成特征，请人工检查 Markdown"
    fi
fi

log "🎉 Phase 2 端到端验收通过！"
exit 0
