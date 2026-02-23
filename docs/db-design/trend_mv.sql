-- 草案：月度趋势物化视图（示例，不可直接执行）
-- 目标：避免 >90d 长窗趋势查询超时，支撑 posts/comments/score_sum 及简易 velocity。
-- 依赖：posts_raw.is_current = true，comments 全量；按月聚合，保持稳态查询。

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_trend AS
WITH monthly AS (
    SELECT
        date_trunc('month', created_at)::date AS month_start,
        COUNT(*) AS posts_cnt,
        0::bigint AS comments_cnt,
        SUM(score)::bigint AS score_sum
    FROM posts_raw
    WHERE is_current = true
    GROUP BY 1
    UNION ALL
    SELECT
        date_trunc('month', created_utc)::date AS month_start,
        0::bigint AS posts_cnt,
        COUNT(*) AS comments_cnt,
        SUM(score)::bigint AS score_sum
    FROM comments
    GROUP BY 1
),
agg AS (
    SELECT
        month_start,
        SUM(posts_cnt) AS posts_cnt,
        SUM(comments_cnt) AS comments_cnt,
        SUM(score_sum) AS score_sum
    FROM monthly
    GROUP BY 1
)
SELECT
    month_start,
    posts_cnt,
    comments_cnt,
    score_sum,
    /* 简易 velocity：与上月差值，可在生成侧再算 L30/L90 比率 */
    posts_cnt - LAG(posts_cnt) OVER (ORDER BY month_start)        AS posts_velocity_mom,
    comments_cnt - LAG(comments_cnt) OVER (ORDER BY month_start)  AS comments_velocity_mom,
    score_sum - LAG(score_sum) OVER (ORDER BY month_start)        AS score_velocity_mom
FROM agg
ORDER BY month_start;

CREATE INDEX IF NOT EXISTS idx_mv_monthly_trend_month ON mv_monthly_trend(month_start);

-- 刷新策略（建议运维脚本/定时任务执行）：
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_trend;
-- 可定义过期阈值（例如 48h 未刷新则标记降级）。
