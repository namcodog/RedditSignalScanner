-- 覆盖率与重复检查（只读）
\echo '1) 重复最新检查 - posts'
SELECT post_id, COUNT(*) AS cnt FROM post_scores WHERE is_latest GROUP BY post_id HAVING COUNT(*)>1 LIMIT 20;

\echo '2) 重复最新检查 - comments'
SELECT comment_id, COUNT(*) AS cnt FROM comment_scores WHERE is_latest GROUP BY comment_id HAVING COUNT(*)>1 LIMIT 20;

\echo '3) 覆盖率 - 标签 (comments)'
SELECT COUNT(*) AS total_labels,
       COUNT(DISTINCT content_id) FILTER (WHERE content_type='comment') AS labeled_comments
FROM content_labels;

\echo '4) 覆盖率 - 标签 (posts)'
SELECT COUNT(*) AS total_labels,
       COUNT(DISTINCT content_id) FILTER (WHERE content_type='post') AS labeled_posts
FROM content_labels;

\echo '5) 空 tags_analysis - posts'
SELECT COUNT(*) AS empty_tags FROM post_scores WHERE is_latest AND (tags_analysis='{}'::jsonb OR tags_analysis IS NULL);

\echo '6) 空 tags_analysis - comments'
SELECT COUNT(*) AS empty_tags FROM comment_scores WHERE is_latest AND (tags_analysis='{}'::jsonb OR tags_analysis IS NULL);

\echo '7) rule_version 分布 - posts'
SELECT rule_version, COUNT(*) FROM post_scores GROUP BY rule_version ORDER BY COUNT(*) DESC;

\echo '8) rule_version 分布 - comments'
SELECT rule_version, COUNT(*) FROM comment_scores GROUP BY rule_version ORDER BY COUNT(*) DESC;
