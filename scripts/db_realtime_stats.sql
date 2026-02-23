-- Realtime DB stats templates (read-only)
-- Usage (local):
--   psql -d reddit_signal_scanner -U postgres -h localhost -f scripts/db_realtime_stats.sql

-- 1) Community status / tier / blacklist / health
SELECT status, COUNT(*) AS cnt
FROM community_pool
GROUP BY status
ORDER BY cnt DESC, status;

SELECT tier, COUNT(*) AS cnt
FROM community_pool
GROUP BY tier
ORDER BY cnt DESC, tier;

SELECT is_blacklisted, COUNT(*) AS cnt
FROM community_pool
GROUP BY is_blacklisted
ORDER BY is_blacklisted DESC;

SELECT health_status, COUNT(*) AS cnt
FROM community_pool
GROUP BY health_status
ORDER BY cnt DESC, health_status;

-- 2) Category coverage
SELECT category_key,
       COUNT(*) AS total_cnt,
       COUNT(*) FILTER (WHERE is_primary) AS primary_cnt
FROM community_category_map
GROUP BY category_key
ORDER BY total_cnt DESC, category_key;

-- 3) Primary count check (0 or >1 are anomalies)
SELECT community_id,
       COUNT(*) FILTER (WHERE is_primary) AS primary_cnt
FROM community_category_map
GROUP BY community_id
HAVING COUNT(*) FILTER (WHERE is_primary) <> 1
ORDER BY primary_cnt DESC, community_id;

-- 4) Category cache drift (map -> cache)
SELECT cp.id,
       cp.name,
       COALESCE(cp.categories, '[]'::jsonb) AS cache_categories,
       COALESCE(m.map_categories, '[]'::jsonb) AS map_categories
FROM community_pool cp
LEFT JOIN LATERAL (
    SELECT to_jsonb(array_agg(category_key ORDER BY is_primary DESC, category_key)) AS map_categories
    FROM community_category_map
    WHERE community_id = cp.id
) m ON true
WHERE COALESCE(cp.categories, '[]'::jsonb) <> COALESCE(m.map_categories, '[]'::jsonb)
ORDER BY cp.id
LIMIT 100;

-- 5) posts_raw community_id completeness
SELECT COUNT(*) AS null_community_id
FROM posts_raw
WHERE community_id IS NULL;

-- 6) SCD2 current duplicates (should be 0)
SELECT source, source_post_id, COUNT(*) AS current_cnt
FROM posts_raw
WHERE is_current = true
GROUP BY source, source_post_id
HAVING COUNT(*) > 1
ORDER BY current_cnt DESC, source, source_post_id
LIMIT 200;

-- 7) Score latest uniqueness (should be 0)
SELECT post_id, COUNT(*) AS latest_cnt
FROM post_scores
WHERE is_latest = true
GROUP BY post_id
HAVING COUNT(*) > 1
ORDER BY latest_cnt DESC, post_id
LIMIT 200;

SELECT comment_id, COUNT(*) AS latest_cnt
FROM comment_scores
WHERE is_latest = true
GROUP BY comment_id
HAVING COUNT(*) > 1
ORDER BY latest_cnt DESC, comment_id
LIMIT 200;

-- 8) Hard orphan counts (should be 0)
SELECT COUNT(*) AS hard_orphan_labels
FROM content_labels cl
LEFT JOIN posts_hot ph
  ON cl.content_type = 'post' AND ph.id = cl.content_id
LEFT JOIN comments c
  ON cl.content_type = 'comment' AND c.id = cl.content_id
WHERE (cl.content_type = 'post' AND ph.id IS NULL)
   OR (cl.content_type = 'comment' AND c.id IS NULL);

SELECT COUNT(*) AS hard_orphan_entities
FROM content_entities ce
LEFT JOIN posts_hot ph
  ON ce.content_type = 'post' AND ph.id = ce.content_id
LEFT JOIN comments c
  ON ce.content_type = 'comment' AND c.id = ce.content_id
WHERE (ce.content_type = 'post' AND ph.id IS NULL)
   OR (ce.content_type = 'comment' AND c.id IS NULL);

-- 9) Soft orphan counts (retention window: 30 days)
SELECT COUNT(*) AS soft_orphan_labels
FROM content_labels cl
LEFT JOIN posts_hot ph
  ON cl.content_type = 'post' AND ph.id = cl.content_id
LEFT JOIN comments c
  ON cl.content_type = 'comment' AND c.id = cl.content_id
WHERE cl.created_at < (NOW() - (30 * interval '1 day'))
  AND (
    (cl.content_type = 'post' AND ph.id IS NOT NULL AND ph.expires_at < (NOW() - (30 * interval '1 day')))
    OR
    (cl.content_type = 'comment' AND c.id IS NOT NULL AND c.removed_by_category IS NOT NULL)
  );

SELECT COUNT(*) AS soft_orphan_entities
FROM content_entities ce
LEFT JOIN posts_hot ph
  ON ce.content_type = 'post' AND ph.id = ce.content_id
LEFT JOIN comments c
  ON ce.content_type = 'comment' AND c.id = ce.content_id
WHERE ce.created_at < (NOW() - (30 * interval '1 day'))
  AND (
    (ce.content_type = 'post' AND ph.id IS NOT NULL AND ph.expires_at < (NOW() - (30 * interval '1 day')))
    OR
    (ce.content_type = 'comment' AND c.id IS NOT NULL AND c.removed_by_category IS NOT NULL)
  );

-- 10) MV refresh recency (from maintenance_audit)
SELECT task_name,
       MAX(ended_at) AS last_run_at,
       MAX(affected_rows) AS last_affected_rows
FROM maintenance_audit
WHERE task_name IN (
    'refresh_mv_monthly_trend',
    'refresh_posts_latest',
    'refresh_post_comment_stats'
)
GROUP BY task_name
ORDER BY task_name;
