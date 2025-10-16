#!/bin/bash

# 自动爬取监控脚本
# 用途：实时监控 Celery 自动爬取任务的执行情况

echo "🔍 Reddit Signal Scanner - 自动爬取监控"
echo "========================================"
echo ""

# 检查服务状态
echo "📊 服务状态检查："
echo ""

# Celery Beat
if ps aux | grep "celery.*beat" | grep -v grep > /dev/null; then
    echo "  ✅ Celery Beat: 运行中"
else
    echo "  ❌ Celery Beat: 未运行"
fi

# Celery Worker
if ps aux | grep "celery.*worker" | grep -v grep > /dev/null; then
    echo "  ✅ Celery Worker: 运行中"
else
    echo "  ❌ Celery Worker: 未运行"
fi

# Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "  ✅ Redis: 运行中"
else
    echo "  ❌ Redis: 未运行"
fi

# PostgreSQL
if psql -d reddit_scanner -c "SELECT 1;" > /dev/null 2>&1; then
    echo "  ✅ PostgreSQL: 运行中"
else
    echo "  ❌ PostgreSQL: 未运行"
fi

echo ""
echo "📈 数据统计："
echo ""

# Redis 缓存
CACHE_COUNT=$(redis-cli -n 5 KEYS "reddit:posts:*" | wc -l | xargs)
echo "  Redis 缓存社区数: $CACHE_COUNT"

# PostgreSQL 统计
psql -d reddit_scanner -c "
SELECT 
    '  总社区数: ' || COUNT(*) as metric
FROM community_cache
UNION ALL
SELECT 
    '  最近1小时爬取: ' || COUNT(CASE WHEN last_crawled_at > NOW() - INTERVAL '1 hour' THEN 1 END)
FROM community_cache
UNION ALL
SELECT 
    '  总帖子数: ' || SUM(posts_cached)
FROM community_cache
UNION ALL
SELECT 
    '  平均帖子数: ' || ROUND(AVG(posts_cached), 1)
FROM community_cache;
" -t

echo ""
echo "🕐 最近爬取记录 (Top 5):"
psql -d reddit_scanner -c "
SELECT 
    community_name,
    posts_cached as posts,
    TO_CHAR(last_crawled_at, 'HH24:MI:SS') as time
FROM community_cache
ORDER BY last_crawled_at DESC
LIMIT 5;
"

echo ""
echo "📅 下次自动爬取时间："
echo "  每小时整点执行 (例如: 20:00, 21:00, 22:00)"
NEXT_HOUR=$(date -v+1H "+%H:00")
echo "  下次执行: 今天 $NEXT_HOUR"

echo ""
echo "📋 Celery Beat 最近任务 (最近 10 条):"
tail -100 /tmp/celery_beat.log | grep "Scheduler: Sending" | tail -10

echo ""
echo "🔄 实时监控模式 (按 Ctrl+C 退出):"
echo "   tail -f /tmp/celery_worker.log | grep -E '(crawl|reddit|success|error)'"

