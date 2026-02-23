#!/bin/bash
# 监控评论回补进度

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🔍 评论回补监控（每 30 秒刷新）"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# 记录开始时间
START_TIME=$(date +%s)
START_COMMENTS=$(psql -d reddit_signal_scanner -t -c "SELECT COUNT(*) FROM comments" | xargs)

echo "📊 初始状态："
echo "  - 开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  - 初始评论数: $START_COMMENTS"
echo ""

CHECK_COUNT=0

while true; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    
    echo "════════════════════════════════════════════════════════════════════════════════"
    echo "📊 第 $CHECK_COUNT 次检查 - $(date '+%H:%M:%S') (运行 ${ELAPSED_MIN} 分钟)"
    echo "════════════════════════════════════════════════════════════════════════════════"
    
    # 获取当前统计
    psql -d reddit_signal_scanner -c "
    SELECT
        '评论总数' as 指标,
        COUNT(*)::text as 数值
    FROM comments

    UNION ALL

    SELECT
        '已抓帖子数',
        COUNT(DISTINCT source_post_id)::text
    FROM comments

    UNION ALL

    SELECT
        '涉及社区数',
        COUNT(DISTINCT subreddit)::text
    FROM comments

    UNION ALL

    SELECT
        '标签总数',
        COUNT(*)::text
    FROM content_labels
    WHERE content_type = 'comment'

    UNION ALL

    SELECT
        '实体总数',
        COUNT(*)::text
    FROM content_entities
    WHERE content_type = 'comment'
    "
    
    # 计算速率
    CURRENT_COMMENTS=$(psql -d reddit_signal_scanner -t -c "SELECT COUNT(*) FROM comments" | xargs)
    NEW_COMMENTS=$((CURRENT_COMMENTS - START_COMMENTS))
    
    if [ $ELAPSED -gt 0 ]; then
        RATE_PER_MIN=$((NEW_COMMENTS * 60 / ELAPSED))
        echo ""
        echo "📈 速率统计："
        echo "  - 新增评论: $NEW_COMMENTS 条"
        echo "  - 平均速率: ~$RATE_PER_MIN 评论/分钟"
        
        # 预估剩余时间（假设目标 500,000 条）
        TARGET=500000
        REMAINING=$((TARGET - CURRENT_COMMENTS))
        if [ $RATE_PER_MIN -gt 0 ] && [ $REMAINING -gt 0 ]; then
            ETA_MIN=$((REMAINING / RATE_PER_MIN))
            ETA_HOUR=$((ETA_MIN / 60))
            ETA_MIN_MOD=$((ETA_MIN % 60))
            echo "  - 剩余评论: $REMAINING 条"
            echo "  - 预计剩余时间: ~${ETA_HOUR}小时${ETA_MIN_MOD}分钟"
            
            # 计算预计完成时间
            ETA_TIMESTAMP=$((CURRENT_TIME + ETA_MIN * 60))
            ETA_TIME=$(date -r $ETA_TIMESTAMP '+%H:%M:%S')
            echo "  - 预计完成时间: 今天 $ETA_TIME"
        fi
        
        # 计算进度百分比
        PROGRESS=$((CURRENT_COMMENTS * 100 / TARGET))
        echo "  - 完成进度: ${PROGRESS}%"
    fi
    
    # 每 3 次检查（90 秒）显示社区分布
    if [ $((CHECK_COUNT % 3)) -eq 0 ]; then
        echo ""
        echo "📊 社区分布（Top 10）："
        psql -d reddit_signal_scanner -c "
        SELECT
            subreddit as 社区,
            COUNT(*) as 评论数,
            COUNT(DISTINCT source_post_id) as 帖子数
        FROM comments
        GROUP BY subreddit
        ORDER BY COUNT(*) DESC
        LIMIT 10
        "
        
        echo ""
        echo "🏷️ 标签分布（Top 10）："
        psql -d reddit_signal_scanner -c "
        SELECT 
            category as 类别,
            COUNT(*) as 数量
        FROM content_labels
        WHERE content_type = 'comment'
        GROUP BY category
        ORDER BY COUNT(*) DESC
        LIMIT 10
        "
    fi
    
    echo ""
    echo "⏳ 下次检查: 30 秒后..."
    echo ""
    
    sleep 30
done

