#!/bin/bash
# 端到端测试脚本（详细输出版本）

set -e

BACKEND_PORT=${BACKEND_PORT:-8006}
PYTHON=${PYTHON:-/opt/homebrew/bin/python3.11}

echo "==> Running end-to-end tests ..."
echo ""

# 1. 检查服务状态
echo "1️⃣  检查服务状态 ..."
redis-cli ping > /dev/null || (echo "❌ Redis未运行！请先运行: make redis-start" && exit 1)
curl -s http://localhost:${BACKEND_PORT}/ > /dev/null || (echo "❌ Backend未运行！请先运行: make dev-backend" && exit 1)
ps aux | grep "celery.*worker" | grep -v grep > /dev/null || (echo "❌ Celery Worker未运行！请先运行: make celery-restart" && exit 1)
echo "   ✅ 所有服务运行正常"
echo ""

# 2. 运行端到端测试
echo "2️⃣  运行端到端测试脚本 ..."
TIMESTAMP=$(date +%s)
EMAIL="e2e-test-${TIMESTAMP}@example.com"

echo "   注册用户: $EMAIL"
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:${BACKEND_PORT}/api/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"TestPass123\"}")

TOKEN=$(echo $REGISTER_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
test -n "$TOKEN" || (echo "❌ 注册失败" && exit 1)
echo "   ✅ 注册成功"
echo ""

echo "   创建分析任务 ..."
TASK_RESPONSE=$(curl -s -X POST http://localhost:${BACKEND_PORT}/api/analyze \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"product_description":"AI-powered note-taking app for researchers"}')

TASK_ID=$(echo $TASK_RESPONSE | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
test -n "$TASK_ID" || (echo "❌ 任务创建失败" && exit 1)
echo "   ✅ 任务创建成功: $TASK_ID"
echo ""

echo "   等待任务完成 ..."
for i in {1..10}; do
    sleep 1
    STATUS=$(curl -s http://localhost:${BACKEND_PORT}/api/status/$TASK_ID \
        -H "Authorization: Bearer $TOKEN" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "     ${i}s: $STATUS"
    if [ "$STATUS" = "completed" ]; then
        break
    fi
done

test "$STATUS" = "completed" || (echo "❌ 任务未完成" && exit 1)
echo "   ✅ 任务完成"
echo ""

echo "   获取分析报告 ..."
REPORT=$(curl -s http://localhost:${BACKEND_PORT}/api/report/$TASK_ID \
    -H "Authorization: Bearer $TOKEN")

echo "$REPORT" > /tmp/e2e_test_report.json

# 3. 使用Python解析并显示详细结果
$PYTHON << 'PYEOF'
import json

with open('/tmp/e2e_test_report.json') as f:
    r = json.load(f)

# 新的API响应格式
report = r.get('report', {})
metadata = report.get('metadata', {})

pain_points = report.get('pain_points', [])
competitors = report.get('competitors', [])
opportunities = report.get('opportunities', [])

pain_count = len(pain_points)
comp_count = len(competitors)
opp_count = len(opportunities)

# 从metadata获取统计信息
posts = metadata.get('posts_analyzed', 0)
cache_rate = metadata.get('cache_hit_rate', 0)
duration = metadata.get('processing_time_seconds', 0)
communities = metadata.get('communities_analyzed', [])

print("")
print("=== 测试结果 ===")
print(f"   痛点数: {pain_count} (目标≥5)")
print(f"   竞品数: {comp_count} (目标≥3)")
print(f"   机会数: {opp_count} (目标≥3)")
print("")

print("=== 数据来源 ===")
print(f"   社区数: {len(communities)}")
print(f"   社区列表: {', '.join(communities[:5])}{'...' if len(communities) > 5 else ''}")
print(f"   帖子数: {posts}")
print(f"   缓存命中率: {cache_rate}%")
print(f"   分析耗时: {duration}秒")
print("")

print("=== 信号示例 ===")
if pain_count > 0:
    print("   💢 痛点示例:")
    for i, pp in enumerate(pain_points[:2], 1):
        desc = pp.get('description', '')[:70]
        freq = pp.get('frequency', 0)
        sentiment = pp.get('sentiment_score', 0)
        print(f"     {i}. {desc}... (提及:{freq}次, 情感:{sentiment})")

if comp_count > 0:
    print("   🏢 竞品示例:")
    for i, comp in enumerate(competitors[:2], 1):
        name = comp.get('name', 'N/A')
        mentions = comp.get('mentions', 0)
        sentiment = comp.get('sentiment', 'N/A')
        print(f"     {i}. {name} (提及:{mentions}次, 情感:{sentiment})")

if opp_count > 0:
    print("   💡 机会示例:")
    for i, opp in enumerate(opportunities[:2], 1):
        desc = opp.get('description', '')[:70]
        users = opp.get('potential_users', 'N/A')
        print(f"     {i}. {desc}... (潜在用户:{users})")

print("")
print("=== 统计摘要 ===")
print(f"   总信号数: {pain_count + comp_count + opp_count}")
if pain_count > 0:
    avg_sentiment = sum(p.get('sentiment_score', 0) for p in pain_points) / pain_count
    print(f"   平均痛点情感分数: {avg_sentiment:.2f}")
if comp_count > 0:
    avg_mentions = sum(c.get('mentions', 0) for c in competitors) / comp_count
    print(f"   竞品平均提及次数: {avg_mentions:.1f}")

print("")

# 验收判断
if pain_count >= 5 and comp_count >= 3 and opp_count >= 3:
    print("✅ 端到端测试通过！")
    exit(0)
else:
    print("❌ 端到端测试失败！")
    if pain_count < 5:
        print(f"   - 痛点数不足: {pain_count} < 5")
    if comp_count < 3:
        print(f"   - 竞品数不足: {comp_count} < 3")
    if opp_count < 3:
        print(f"   - 机会数不足: {opp_count} < 3")
    exit(1)
PYEOF

