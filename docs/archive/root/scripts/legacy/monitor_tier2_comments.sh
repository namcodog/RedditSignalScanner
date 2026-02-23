#!/bin/bash
# 监控T2评论抓取进度

while true; do
  clear
  echo "=========================================="
  echo "📊 T2社区评论抓取进度监控"
  echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "=========================================="
  echo ""
  
  psql "postgresql://postgres:postgres@localhost:5432/reddit_signal_scanner" -c "
SELECT 
  LOWER(COALESCE(p.subreddit, c.subreddit)) AS subreddit,
  COUNT(DISTINCT p.source_post_id) AS posts,
  COUNT(DISTINCT c.reddit_comment_id) AS comments,
  ROUND(COUNT(DISTINCT c.reddit_comment_id)::numeric / NULLIF(COUNT(DISTINCT p.source_post_id), 0), 1) AS avg_comments
FROM posts_raw p
LEFT JOIN comments c ON p.source_post_id = c.source_post_id
WHERE LOWER(COALESCE(p.subreddit, c.subreddit)) IN (
  'amazondspdrivers', 'amazonfc', 'amazonvine',
  'flipping', 'instacartshoppers', 'walmartemployees',
  'amazonreviews', 'ecommerce', 'shopify', 'walmart', 'walmartworkers'
)
GROUP BY LOWER(COALESCE(p.subreddit, c.subreddit))
ORDER BY comments DESC;
"
  
  echo ""
  echo "按 Ctrl+C 退出监控"
  sleep 10
done
