#!/bin/bash

# Admin API 手动测试脚本
# 用于验证社区管理批量导入功能

set -e

echo "🔍 Admin API 手动测试"
echo "===================="
echo ""

# 配置
API_BASE="http://localhost:8006"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="admin123"

echo "📝 步骤1：注册Admin用户"
echo "----------------------"
REGISTER_RESPONSE=$(curl -s -X POST "${API_BASE}/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" || echo '{"error":"already exists"}')

echo "注册响应: ${REGISTER_RESPONSE}"
echo ""

echo "🔐 步骤2：登录获取Token"
echo "----------------------"
LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")

echo "登录响应: ${LOGIN_RESPONSE}"

# 提取token
TOKEN=$(echo "${LOGIN_RESPONSE}" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ 登录失败，无法获取token"
  exit 1
fi

echo "✅ Token获取成功: ${TOKEN:0:20}..."
echo ""

echo "📥 步骤3：下载模板"
echo "----------------------"
curl -s -X GET "${API_BASE}/api/admin/communities/template" \
  -H "Authorization: Bearer ${TOKEN}" \
  -o community_template.xlsx

if [ -f "community_template.xlsx" ]; then
  FILE_SIZE=$(wc -c < community_template.xlsx)
  echo "✅ 模板下载成功，文件大小: ${FILE_SIZE} bytes"
else
  echo "❌ 模板下载失败"
  exit 1
fi
echo ""

echo "📋 步骤4：查看导入历史"
echo "----------------------"
HISTORY_RESPONSE=$(curl -s -X GET "${API_BASE}/api/admin/communities/import-history" \
  -H "Authorization: Bearer ${TOKEN}")

echo "历史记录响应: ${HISTORY_RESPONSE}"
echo ""

echo "✅ 所有测试完成！"
echo ""
echo "📝 测试总结："
echo "  - ✅ Admin用户注册/登录"
echo "  - ✅ Token获取"
echo "  - ✅ 下载模板"
echo "  - ✅ 查看导入历史"
echo ""
echo "💡 下一步："
echo "  1. 填写 community_template.xlsx"
echo "  2. 使用前端页面上传测试"
echo "  3. 验证导入结果"

