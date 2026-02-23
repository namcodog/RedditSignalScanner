# 生产环境数据库修复与加固手册

目标：在确保**零数据丢失**的前提下，将数据库结构与开发环境的修复保持一致，包含评论关联、SCD2 自动关窗、缓存计数防脏值、关键索引完善。

## 前置条件
- 确认维护窗口：建议只读切换或低流量时段。
- 账户：具备 SUPERUSER/DDL 权限的数据库账号。
- 环境变量：`PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE` 预设，或在命令中显式传入。
- 备份目录：本地或安全存储，例如 `tmp/prod_backup_$(date +%Y%m%d%H%M).dump`.

## 步骤总览
1. **全量备份**（必做，可回滚）。
2. **健康检查**（确认异常记录数量）。
3. **无损变更 SQL**（索引、约束、触发器、回填）。
4. **校验与回归**（约束命中数、关键查询计划）。
5. **观察与回滚预案**（如有异常，立即用备份恢复）。

## 1) 备份
```bash
pg_dump -Fc -f tmp/prod_backup_$(date +%Y%m%d%H%M).dump
```
> 如需远程备份，可通过 ssh 隧道或在数据库所在主机执行。

## 2) 健康检查（执行前记录基线）
```sql
-- 孤儿评论
SELECT count(*) AS orphan_comments FROM comments WHERE post_id IS NULL;

-- posts_raw 当前版本重复（理应为 0）
SELECT source, source_post_id, count(*) FILTER (WHERE is_current) AS current_cnt
FROM posts_raw
GROUP BY 1,2 HAVING count(*) FILTER (WHERE is_current) > 1
LIMIT 50;

-- community_cache 计数字段异常
SELECT
  count(*) FILTER (WHERE empty_hit < 0 OR success_hit < 0 OR failure_hit < 0 OR avg_valid_posts < 0 OR total_posts_fetched < 0) AS negative_counts,
  count(*) FILTER (WHERE crawl_quality_score IS NULL) AS null_quality_score
FROM community_cache;
```

## 3) 无损变更 SQL（事务内执行）
> 下列语句可整体保存为 `prod_fix.sql`，通过 `psql -v ON_ERROR_STOP=1 -f prod_fix.sql` 执行。若任何一步失败会自动回滚。

```sql
BEGIN;
SET LOCAL statement_timeout = 0;
SET LOCAL timezone = 'UTC';

-- 3.1 comments：补列、回填、索引、FK、收紧为 NOT NULL
ALTER TABLE public.comments ADD COLUMN IF NOT EXISTS post_id bigint;

-- 回填（按 source/source_post_id 匹配当前帖子；若不存在则插入占位贴）
WITH missing AS (
  SELECT c.source,
         c.source_post_id,
         min(c.subreddit)    AS subreddit,
         min(c.created_utc)  AS created_utc,
         min(c.author_id)    AS author_id,
         min(c.author_name)  AS author_name,
         min(c.score)        AS score,
         min(c.body)         AS sample_body
  FROM comments c
  WHERE c.post_id IS NULL
  GROUP BY c.source, c.source_post_id
),
inserted AS (
  INSERT INTO posts_raw (
      source, source_post_id, created_at, fetched_at, valid_from,
      is_current, author_id, author_name, title, body, subreddit, score, valid_to
  )
  SELECT m.source,
         m.source_post_id,
         COALESCE(m.created_utc, now()),
         now(),
         COALESCE(m.created_utc, now()),
         true,
         m.author_id,
         m.author_name,
         '[placeholder missing post]',
         substring(COALESCE(m.sample_body, ''), 1, 500),
         COALESCE(m.subreddit, 'r/unknown'),
         COALESCE(m.score, 0),
         '9999-12-31 00:00:00+00'::timestamptz
  FROM missing m
  ON CONFLICT DO NOTHING
  RETURNING 1
),
updated AS (
  UPDATE comments c
  SET post_id = p.id
  FROM posts_raw p
  WHERE c.post_id IS NULL
    AND p.source = c.source
    AND p.source_post_id = c.source_post_id
  RETURNING 1
)
SELECT
  (SELECT count(*) FROM missing)  AS missing_keys,
  (SELECT count(*) FROM inserted) AS inserted_posts,
  (SELECT count(*) FROM updated)  AS updated_comments;

CREATE INDEX IF NOT EXISTS idx_comments_post_id ON public.comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON public.comments(parent_id);

ALTER TABLE public.comments
  DROP CONSTRAINT IF EXISTS fk_comments_posts_raw,
  ADD CONSTRAINT fk_comments_posts_raw
    FOREIGN KEY (post_id) REFERENCES public.posts_raw(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.comments ALTER COLUMN post_id SET NOT NULL;

-- 3.2 posts_raw：SCD2 自动关窗触发器（确保唯一当前版本）
CREATE OR REPLACE FUNCTION public.trg_posts_raw_enforce_scd2()
RETURNS trigger AS $$
BEGIN
  IF NEW.is_current THEN
    UPDATE public.posts_raw
      SET is_current = false,
          valid_to   = LEAST(COALESCE(NEW.valid_from, now()), now())
      WHERE source = NEW.source
        AND source_post_id = NEW.source_post_id
        AND is_current = true
        AND id <> COALESCE(NEW.id, -1);
  END IF;

  IF NEW.valid_to IS NULL THEN
    NEW.valid_to := '9999-12-31 00:00:00+00'::timestamptz;
  END IF;
  IF NEW.valid_from IS NULL THEN
    NEW.valid_from := now();
  END IF;
  IF NEW.valid_from >= NEW.valid_to THEN
    NEW.valid_to := NEW.valid_from + interval '1 second';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS enforce_scd2_posts_raw ON public.posts_raw;
CREATE TRIGGER enforce_scd2_posts_raw
BEFORE INSERT OR UPDATE ON public.posts_raw
FOR EACH ROW
EXECUTE FUNCTION public.trg_posts_raw_enforce_scd2();

-- 3.3 posts_raw 默认值（UTC 远未来）
ALTER TABLE public.posts_raw
  ALTER COLUMN valid_to SET DEFAULT '9999-12-31 00:00:00+00'::timestamptz;

-- 3.4 community_cache：默认值 + 非负/区间约束 + 调度索引
ALTER TABLE public.community_cache
  ALTER COLUMN empty_hit           SET DEFAULT 0,
  ALTER COLUMN success_hit         SET DEFAULT 0,
  ALTER COLUMN failure_hit         SET DEFAULT 0,
  ALTER COLUMN avg_valid_posts     SET DEFAULT 0,
  ALTER COLUMN total_posts_fetched SET DEFAULT 0,
  ALTER COLUMN crawl_quality_score SET DEFAULT 0.0;

ALTER TABLE public.community_cache
  ADD CONSTRAINT IF NOT EXISTS ck_cache_empty_hit_nonneg   CHECK (empty_hit >= 0),
  ADD CONSTRAINT IF NOT EXISTS ck_cache_success_hit_nonneg CHECK (success_hit >= 0),
  ADD CONSTRAINT IF NOT EXISTS ck_cache_failure_hit_nonneg CHECK (failure_hit >= 0),
  ADD CONSTRAINT IF NOT EXISTS ck_cache_avg_valid_nonneg   CHECK (avg_valid_posts >= 0),
  ADD CONSTRAINT IF NOT EXISTS ck_cache_total_nonneg       CHECK (total_posts_fetched >= 0),
  ADD CONSTRAINT IF NOT EXISTS ck_cache_quality_range      CHECK (crawl_quality_score BETWEEN 0 AND 10);

CREATE INDEX IF NOT EXISTS idx_cache_ttl_active
  ON public.community_cache (is_active, last_crawled_at, ttl_seconds)
  WHERE is_active = true;

-- 3.5 posts_hot：过期/分社区查询索引
CREATE INDEX IF NOT EXISTS idx_posts_hot_subreddit_expires
  ON public.posts_hot (subreddit, expires_at);

COMMIT;
```

## 4) 变更后校验
```sql
-- 孤儿评论应为 0
SELECT count(*) AS orphan_comments FROM comments WHERE post_id IS NULL;

-- SCD2 当前版本重复应为 0
SELECT count(*) FROM (
  SELECT 1 FROM posts_raw GROUP BY source, source_post_id HAVING count(*) FILTER (WHERE is_current) > 1
) t;

-- community_cache 负数或 NULL 计数
SELECT
  count(*) FILTER (WHERE empty_hit < 0 OR success_hit < 0 OR failure_hit < 0 OR avg_valid_posts < 0 OR total_posts_fetched < 0) AS negative_counts,
  count(*) FILTER (WHERE crawl_quality_score IS NULL) AS null_quality_score
FROM community_cache;
```

## 5) 回归与监控
- 跑核心读写用例/自动化测试，关注新增触发器、CHECK/FK 是否阻断合法写入。
- 观察慢查询（特别是评论树、热帖过期、社区调度），确认新索引被命中。
- 保留本次备份，异常时可 `pg_restore` 全量恢复。

## 回滚预案
- 使用备份恢复：`pg_restore -c -d <database> tmp/prod_backup_YYYYMMDDHHMM.dump`
- 如仅部分变更需撤销，可按需要 `DROP TRIGGER`, `DROP INDEX`, `ALTER TABLE ... DROP CONSTRAINT`。

## 备注
- 所有 DDL 已加 IF NOT EXISTS/防重复，支持可重入执行。
- 回填逻辑会为缺失帖子创建占位行，确保评论不再孤儿；如需改为“严格拒绝”，请先清理或导入缺失帖子，再移除占位插入段落。 
