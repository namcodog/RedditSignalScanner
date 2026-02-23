#!/bin/bash
# 验证次高价值社区抓取结果

set -e

echo "=========================================="
echo "🔍 次高价值社区抓取结果验证"
echo "=========================================="

source backend/.env

echo ""
echo "📊 1. 总体统计"
echo "=========================================="
psql "${DATABASE_URL//+asyncpg/}" -c "
SELECT 
  COUNT(DISTINCT cp.name) as total_communities,
  COUNT(DISTINCT pr.id) as total_posts,
  COUNT(DISTINCT c.id) as total_comments,
  ROUND(COUNT(DISTINCT c.id)::numeric / NULLIF(COUNT(DISTINCT pr.id), 0), 2) as avg_comments_per_post
FROM community_pool cp
LEFT JOIN posts_raw pr ON pr.subreddit = REPLACE(cp.name, 'r/', '')
LEFT JOIN comments c ON c.source_post_id = pr.source_post_id
WHERE cp.tier = 'medium' AND cp.is_active = true;
"

echo ""
echo "📋 2. 每个社区的详细统计"
echo "=========================================="
psql "${DATABASE_URL//+asyncpg/}" -c "
SELECT 
  cp.name,
  COUNT(DISTINCT pr.id) as posts_count,
  COUNT(DISTINCT c.id) as comments_count,
  ROUND(COUNT(DISTINCT c.id)::numeric / NULLIF(COUNT(DISTINCT pr.id), 0), 2) as avg_comments_per_post
FROM community_pool cp
LEFT JOIN posts_raw pr ON pr.subreddit = REPLACE(cp.name, 'r/', '')
LEFT JOIN comments c ON c.source_post_id = pr.source_post_id
WHERE cp.tier = 'medium' AND cp.is_active = true
GROUP BY cp.name
ORDER BY posts_count DESC;
"

echo ""
echo "📅 3. 时间范围检查"
echo "=========================================="
psql "${DATABASE_URL//+asyncpg/}" -c "
SELECT 
  cp.name,
  MIN(pr.created_at)::date as earliest_post,
  MAX(pr.created_at)::date as latest_post,
  COUNT(DISTINCT DATE_TRUNC('month', pr.created_at)) as months_covered
FROM community_pool cp
LEFT JOIN posts_raw pr ON pr.subreddit = REPLACE(cp.name, 'r/', '')
WHERE cp.tier = 'medium' AND cp.is_active = true AND pr.id IS NOT NULL
GROUP BY cp.name
ORDER BY cp.name;
"

echo ""
echo "🎯 4. 成功标准检查"
echo "=========================================="

# 获取统计数据
STATS=$(psql "${DATABASE_URL//+asyncpg/}" -t -c "
SELECT 
  COUNT(DISTINCT cp.name),
  COUNT(DISTINCT pr.id),
  COUNT(DISTINCT c.id)
FROM community_pool cp
LEFT JOIN posts_raw pr ON pr.subreddit = REPLACE(cp.name, 'r/', '')
LEFT JOIN comments c ON c.source_post_id = pr.source_post_id
WHERE cp.tier = 'medium' AND cp.is_active = true;
")

COMMUNITIES=$(echo $STATS | awk '{print $1}')
POSTS=$(echo $STATS | awk '{print $2}')
COMMENTS=$(echo $STATS | awk '{print $3}')

echo "社区覆盖率：$COMMUNITIES/15"
if [ "$COMMUNITIES" -eq 15 ]; then
    echo "  ✅ 通过（100%覆盖）"
else
    echo "  ❌ 失败（未达到100%）"
fi

echo ""
echo "帖子数量：$POSTS"
if [ "$POSTS" -ge 10000 ]; then
    echo "  ✅ 通过（≥10,000）"
else
    echo "  ⚠️ 警告（<10,000）"
fi

echo ""
echo "评论数量：$COMMENTS"
if [ "$COMMENTS" -ge 50000 ]; then
    echo "  ✅ 通过（≥50,000）"
else
    echo "  ⚠️ 警告（<50,000）"
fi

echo ""
echo "=========================================="
echo "✅ 验证完成！"
echo "=========================================="

