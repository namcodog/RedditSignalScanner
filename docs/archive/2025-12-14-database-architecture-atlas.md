# Database Architecture Atlas（本地生产库 / 唯一参照）

这份文档回答一句话：**现在这个库里，表/字段/约束到底长什么样？**

- 数据库：`reddit_signal_scanner`
- Schema：`public`
- Alembic 版本：`20251218_000003`
- 表数量：`52`
- 生成时间（UTC）：`2025-12-19T09:22:00.415122+00:00`

## 怎么重新生成（强烈建议每次 DB 升级后跑一次）

```bash
# 1) 指定 DATABASE_URL（不要把密码写进文档）
export DB_ATLAS_DATABASE_URL='postgresql://USER:***@HOST:5432/DBNAME'

# 2) 生成/覆盖本文件
python scripts/generate_db_atlas.py \
  --database-url "$DB_ATLAS_DATABASE_URL" \
  --out "docs/2025-12-14-database-architecture-atlas.md"
```

## ID 字段总表（速查）

| 表 | 字段 | 类型 |
|---|---|---|
| `analyses` | `id` | `uuid` |
| `analyses` | `task_id` | `uuid` |
| `authors` | `author_id` | `character varying` |
| `beta_feedback` | `id` | `uuid` |
| `beta_feedback` | `task_id` | `uuid` |
| `beta_feedback` | `user_id` | `uuid` |
| `cleanup_logs` | `id` | `uuid` |
| `comment_scores` | `comment_id` | `bigint` |
| `comment_scores` | `id` | `uuid` |
| `comment_scores_latest_v` | `comment_id` | `bigint` |
| `comments` | `author_id` | `character varying` |
| `comments` | `community_run_id` | `uuid` |
| `comments` | `crawl_run_id` | `uuid` |
| `comments` | `id` | `bigint` |
| `comments` | `parent_id` | `character varying` |
| `comments` | `post_id` | `bigint` |
| `comments` | `reddit_comment_id` | `character varying` |
| `comments` | `source_post_id` | `character varying` |
| `comments_core_lab_v` | `author_id` | `character varying` |
| `comments_core_lab_v` | `crawl_run_id` | `uuid` |
| `comments_core_lab_v` | `id` | `bigint` |
| `comments_core_lab_v` | `parent_id` | `character varying` |
| `comments_core_lab_v` | `post_id` | `bigint` |
| `comments_core_lab_v` | `reddit_comment_id` | `character varying` |
| `comments_core_lab_v` | `source_post_id` | `character varying` |
| `community_audit` | `community_id` | `bigint` |
| `community_audit` | `id` | `integer` |
| `community_cache` | `last_seen_post_id` | `character varying` |
| `community_category_map` | `community_id` | `integer` |
| `community_import_history` | `id` | `integer` |
| `community_import_history` | `uploaded_by_user_id` | `uuid` |
| `community_pool` | `id` | `integer` |
| `content_entities` | `content_id` | `bigint` |
| `content_entities` | `id` | `bigint` |
| `content_labels` | `content_id` | `bigint` |
| `content_labels` | `id` | `bigint` |
| `crawl_metrics` | `crawl_run_id` | `uuid` |
| `crawl_metrics` | `id` | `integer` |
| `crawler_run_targets` | `crawl_run_id` | `uuid` |
| `crawler_run_targets` | `id` | `uuid` |
| `crawler_runs` | `id` | `uuid` |
| `data_audit_events` | `id` | `bigint` |
| `data_audit_events` | `target_id` | `character varying` |
| `discovered_communities` | `discovered_from_task_id` | `uuid` |
| `discovered_communities` | `id` | `integer` |
| `evidence_posts` | `crawl_run_id` | `uuid` |
| `evidence_posts` | `id` | `integer` |
| `evidence_posts` | `source_post_id` | `character varying` |
| `evidence_posts` | `target_id` | `uuid` |
| `evidences` | `id` | `uuid` |
| `evidences` | `insight_card_id` | `uuid` |
| `facts_quality_audit` | `run_id` | `uuid` |
| `facts_run_logs` | `id` | `uuid` |
| `facts_run_logs` | `task_id` | `uuid` |
| `facts_snapshots` | `id` | `uuid` |
| `facts_snapshots` | `task_id` | `uuid` |
| `feedback_events` | `analysis_id` | `text` |
| `feedback_events` | `id` | `uuid` |
| `feedback_events` | `task_id` | `text` |
| `feedback_events` | `user_id` | `text` |
| `insight_cards` | `id` | `uuid` |
| `insight_cards` | `task_id` | `uuid` |
| `maintenance_audit` | `id` | `bigint` |
| `noise_labels` | `content_id` | `bigint` |
| `noise_labels` | `id` | `integer` |
| `post_embeddings` | `post_id` | `bigint` |
| `post_scores` | `id` | `uuid` |
| `post_scores` | `post_id` | `bigint` |
| `post_scores_latest_v` | `id` | `uuid` |
| `post_scores_latest_v` | `post_id` | `bigint` |
| `post_semantic_labels` | `id` | `bigint` |
| `post_semantic_labels` | `post_id` | `bigint` |
| `posts_archive` | `id` | `bigint` |
| `posts_archive` | `source_post_id` | `character varying` |
| `posts_hot` | `author_id` | `character varying` |
| `posts_hot` | `id` | `bigint` |
| `posts_hot` | `source_post_id` | `character varying` |
| `posts_quarantine` | `id` | `bigint` |
| `posts_quarantine` | `source_post_id` | `character varying` |
| `posts_raw` | `author_id` | `character varying` |
| `posts_raw` | `community_id` | `integer` |
| `posts_raw` | `community_run_id` | `uuid` |
| `posts_raw` | `crawl_run_id` | `uuid` |
| `posts_raw` | `duplicate_of_id` | `bigint` |
| `posts_raw` | `id` | `bigint` |
| `posts_raw` | `source_post_id` | `character varying` |
| `quality_metrics` | `id` | `integer` |
| `reports` | `analysis_id` | `uuid` |
| `reports` | `id` | `uuid` |
| `semantic_audit_logs` | `entity_id` | `bigint` |
| `semantic_audit_logs` | `id` | `integer` |
| `semantic_audit_logs` | `operator_id` | `uuid` |
| `semantic_candidates` | `id` | `integer` |
| `semantic_concepts` | `id` | `integer` |
| `semantic_rules` | `concept_id` | `integer` |
| `semantic_rules` | `id` | `integer` |
| `semantic_terms` | `id` | `bigint` |
| `storage_metrics` | `id` | `bigint` |
| `subreddit_snapshots` | `id` | `bigint` |
| `tasks` | `id` | `uuid` |
| `tasks` | `topic_profile_id` | `character varying` |
| `tasks` | `user_id` | `uuid` |
| `tier_audit_logs` | `id` | `integer` |
| `tier_audit_logs` | `suggestion_id` | `integer` |
| `tier_suggestions` | `id` | `integer` |
| `users` | `id` | `uuid` |
| `users` | `tenant_id` | `uuid` |
| `v_comment_semantic_tasks` | `comment_id` | `bigint` |
| `v_comment_semantic_tasks` | `reddit_comment_id` | `character varying` |
| `v_comment_semantic_tasks` | `source_post_id` | `character varying` |
| `v_post_semantic_tasks` | `post_id` | `bigint` |
| `v_post_semantic_tasks` | `source_post_id` | `character varying` |

说明：这里只是“长得像 ID 的字段”速查；真正语义请看抓取SOP的“ID口径”章节。

## JSON/JSONB 字段总表（速查）

| 表 | 字段 | 类型 |
|---|---|---|
| `analyses` | `action_items` | `jsonb` |
| `analyses` | `insights` | `jsonb` |
| `analyses` | `sources` | `jsonb` |
| `cleanup_logs` | `breakdown` | `jsonb` |
| `comment_scores` | `calculation_log` | `jsonb` |
| `comment_scores` | `entities_extracted` | `jsonb` |
| `comment_scores` | `tags_analysis` | `jsonb` |
| `comment_scores_latest_v` | `calculation_log` | `jsonb` |
| `comment_scores_latest_v` | `entities_extracted` | `jsonb` |
| `comment_scores_latest_v` | `tags_analysis` | `jsonb` |
| `community_audit` | `metrics` | `jsonb` |
| `community_import_history` | `error_details` | `jsonb` |
| `community_import_history` | `summary_preview` | `jsonb` |
| `community_pool` | `categories` | `jsonb` |
| `community_pool` | `description_keywords` | `jsonb` |
| `crawl_metrics` | `tier_assignments` | `json` |
| `crawler_run_targets` | `config` | `jsonb` |
| `crawler_run_targets` | `metrics` | `jsonb` |
| `crawler_runs` | `config` | `jsonb` |
| `crawler_runs` | `metrics` | `jsonb` |
| `data_audit_events` | `new_value` | `jsonb` |
| `data_audit_events` | `old_value` | `jsonb` |
| `discovered_communities` | `discovered_from_keywords` | `jsonb` |
| `discovered_communities` | `metrics` | `jsonb` |
| `facts_quality_audit` | `dynamic_blacklist` | `jsonb` |
| `facts_quality_audit` | `dynamic_whitelist` | `jsonb` |
| `facts_quality_audit` | `insufficient_flags` | `jsonb` |
| `facts_run_logs` | `summary` | `jsonb` |
| `facts_snapshots` | `quality` | `jsonb` |
| `facts_snapshots` | `v2_package` | `jsonb` |
| `feedback_events` | `payload` | `jsonb` |
| `maintenance_audit` | `extra` | `jsonb` |
| `post_scores` | `calculation_log` | `jsonb` |
| `post_scores` | `entities_extracted` | `jsonb` |
| `post_scores` | `tags_analysis` | `jsonb` |
| `post_scores_latest_v` | `calculation_log` | `jsonb` |
| `post_scores_latest_v` | `entities_extracted` | `jsonb` |
| `post_scores_latest_v` | `tags_analysis` | `jsonb` |
| `post_semantic_labels` | `raw_scores` | `json` |
| `posts_archive` | `payload` | `jsonb` |
| `posts_hot` | `content_labels` | `jsonb` |
| `posts_hot` | `entities` | `jsonb` |
| `posts_hot` | `metadata` | `jsonb` |
| `posts_quarantine` | `original_payload` | `jsonb` |
| `posts_raw` | `metadata` | `jsonb` |
| `semantic_audit_logs` | `changes` | `jsonb` |
| `semantic_rules` | `meta` | `json` |
| `storage_metrics` | `notes` | `jsonb` |
| `tier_audit_logs` | `snapshot_after` | `jsonb` |
| `tier_audit_logs` | `snapshot_before` | `jsonb` |
| `tier_suggestions` | `metrics` | `jsonb` |
| `tier_suggestions` | `reasons` | `jsonb` |

## 表清单

```
alembic_version
analyses
analytics_community_history
authors
beta_feedback
business_categories
cleanup_logs
comment_scores
comments
community_audit
community_cache
community_category_map
community_import_history
community_pool
community_roles_map
content_entities
content_labels
crawl_metrics
crawler_run_targets
crawler_runs
data_audit_events
discovered_communities
evidence_posts
evidences
facts_quality_audit
facts_run_logs
facts_snapshots
feedback_events
insight_cards
maintenance_audit
noise_labels
post_embeddings
post_scores
post_semantic_labels
posts_archive
posts_hot
posts_quarantine
posts_raw
quality_metrics
reports
semantic_audit_logs
semantic_candidates
semantic_concepts
semantic_rules
semantic_terms
storage_metrics
subreddit_snapshots
tasks
tier_audit_logs
tier_suggestions
users
vertical_map
```

## 表结构（逐表）

## `alembic_version`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `version_num` | `character varying` | NO | `` |

### 约束

- `alembic_version_pkc` (PRIMARY KEY)：`PRIMARY KEY (version_num)`

### 索引

- `alembic_version_pkc`：`CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)`

## `analyses`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `task_id` | `uuid` | NO | `` |
| `insights` | `jsonb` | NO | `` |
| `sources` | `jsonb` | NO | `` |
| `confidence_score` | `numeric` | YES | `` |
| `analysis_version` | `integer` | NO | `1` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `action_items` | `jsonb` | YES | `` |

### 约束

- `ck_analyses_confidence_range` (CHECK)：`CHECK (confidence_score >= 0.00 AND confidence_score <= 1.00)`
- `ck_analyses_insights_jsonb` (CHECK)：`CHECK (insights IS NULL OR jsonb_typeof(insights) = 'object'::text) NOT VALID`
- `ck_analyses_sources_jsonb` (CHECK)：`CHECK (sources IS NULL OR jsonb_typeof(sources) = 'object'::text) NOT VALID`
- `ck_analyses_version_positive` (CHECK)：`CHECK (analysis_version > 0)`
- `fk_analyses_task_id` (FOREIGN KEY)：`FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE`
- `analyses_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_analyses_task_id` (UNIQUE)：`UNIQUE (task_id, analysis_version)`

### 索引

- `analyses_pkey`：`CREATE UNIQUE INDEX analyses_pkey ON public.analyses USING btree (id)`
- `idx_analyses_task_created`：`CREATE INDEX idx_analyses_task_created ON public.analyses USING btree (task_id, created_at) WHERE (task_id IS NOT NULL)`
- `ix_analyses_confidence_created`：`CREATE INDEX ix_analyses_confidence_created ON public.analyses USING btree (confidence_score DESC, created_at DESC)`
- `ix_analyses_confidence_desc`：`CREATE INDEX ix_analyses_confidence_desc ON public.analyses USING btree (confidence_score DESC)`
- `ix_analyses_created_desc`：`CREATE INDEX ix_analyses_created_desc ON public.analyses USING btree (created_at DESC)`
- `ix_analyses_insights_gin`：`CREATE INDEX ix_analyses_insights_gin ON public.analyses USING gin (insights jsonb_path_ops)`
- `ix_analyses_sources_gin`：`CREATE INDEX ix_analyses_sources_gin ON public.analyses USING gin (sources)`
- `ix_analyses_task_created`：`CREATE INDEX ix_analyses_task_created ON public.analyses USING btree (task_id, created_at DESC)`
- `ix_analyses_version_created`：`CREATE INDEX ix_analyses_version_created ON public.analyses USING btree (analysis_version, created_at DESC)`
- `uq_analyses_task_id`：`CREATE UNIQUE INDEX uq_analyses_task_id ON public.analyses USING btree (task_id, analysis_version)`

## `analytics_community_history`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `report_date` | `date` | NO | `CURRENT_DATE` |
| `subreddit` | `character varying` | NO | `` |
| `active_users_24h` | `integer` | YES | `` |
| `posts_24h` | `integer` | YES | `` |
| `pain_points_count` | `integer` | YES | `` |
| `commercial_density` | `numeric` | YES | `` |
| `c_score` | `numeric` | YES | `` |

### 约束

- `analytics_community_history_pkey` (PRIMARY KEY)：`PRIMARY KEY (report_date, subreddit)`

### 索引

- `analytics_community_history_pkey`：`CREATE UNIQUE INDEX analytics_community_history_pkey ON public.analytics_community_history USING btree (report_date, subreddit)`

## `authors`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `author_id` | `character varying` | NO | `` |
| `author_name` | `character varying` | YES | `` |
| `created_utc` | `timestamp with time zone` | YES | `` |
| `is_bot` | `boolean` | NO | `false` |
| `first_seen_at_global` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |

### 约束

- `pk_authors` (PRIMARY KEY)：`PRIMARY KEY (author_id)`

### 索引

- `pk_authors`：`CREATE UNIQUE INDEX pk_authors ON public.authors USING btree (author_id)`

## `beta_feedback`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `` |
| `task_id` | `uuid` | NO | `` |
| `user_id` | `uuid` | NO | `` |
| `satisfaction` | `integer` | NO | `` |
| `missing_communities` | `ARRAY` | NO | `'{}'::text[]` |
| `comments` | `text` | NO | `''::text` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |

### 约束

- `beta_feedback_satisfaction_check` (CHECK)：`CHECK (satisfaction >= 1 AND satisfaction <= 5)`
- `beta_feedback_task_id_fkey` (FOREIGN KEY)：`FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE`
- `beta_feedback_user_id_fkey` (FOREIGN KEY)：`FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- `beta_feedback_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `beta_feedback_pkey`：`CREATE UNIQUE INDEX beta_feedback_pkey ON public.beta_feedback USING btree (id)`
- `idx_beta_feedback_created_at`：`CREATE INDEX idx_beta_feedback_created_at ON public.beta_feedback USING btree (created_at)`
- `idx_beta_feedback_task_id`：`CREATE INDEX idx_beta_feedback_task_id ON public.beta_feedback USING btree (task_id)`
- `idx_beta_feedback_user_id`：`CREATE INDEX idx_beta_feedback_user_id ON public.beta_feedback USING btree (user_id)`

## `business_categories`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `key` | `character varying` | NO | `` |
| `display_name` | `character varying` | YES | `` |
| `description` | `text` | YES | `` |
| `is_active` | `boolean` | YES | `true` |
| `created_at` | `timestamp with time zone` | YES | `now()` |
| `updated_at` | `timestamp with time zone` | YES | `now()` |

### 约束

- `business_categories_pkey` (PRIMARY KEY)：`PRIMARY KEY (key)`

### 索引

- `business_categories_pkey`：`CREATE UNIQUE INDEX business_categories_pkey ON public.business_categories USING btree (key)`

## `cleanup_logs`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `executed_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `total_records_cleaned` | `integer` | NO | `` |
| `breakdown` | `jsonb` | NO | `` |
| `duration_seconds` | `integer` | YES | `` |
| `success` | `boolean` | NO | `true` |
| `error_message` | `text` | YES | `` |

### 约束

- `cleanup_logs_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `cleanup_logs_pkey`：`CREATE UNIQUE INDEX cleanup_logs_pkey ON public.cleanup_logs USING btree (id)`
- `idx_cleanup_logs_time_success`：`CREATE INDEX idx_cleanup_logs_time_success ON public.cleanup_logs USING btree (executed_at DESC, success, total_records_cleaned)`
- `ix_cleanup_logs_executed_desc`：`CREATE INDEX ix_cleanup_logs_executed_desc ON public.cleanup_logs USING btree (executed_at DESC)`
- `ix_cleanup_logs_success`：`CREATE INDEX ix_cleanup_logs_success ON public.cleanup_logs USING btree (success)`

## `comment_scores`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `comment_id` | `bigint` | NO | `` |
| `llm_version` | `character varying` | NO | `` |
| `rule_version` | `character varying` | NO | `` |
| `scored_at` | `timestamp with time zone` | YES | `now()` |
| `is_latest` | `boolean` | YES | `true` |
| `value_score` | `numeric` | YES | `` |
| `opportunity_score` | `numeric` | YES | `` |
| `business_pool` | `character varying` | YES | `` |
| `sentiment` | `numeric` | YES | `` |
| `purchase_intent_score` | `numeric` | YES | `` |
| `tags_analysis` | `jsonb` | YES | `'{}'::jsonb` |
| `entities_extracted` | `jsonb` | YES | `'[]'::jsonb` |
| `calculation_log` | `jsonb` | YES | `'{}'::jsonb` |

### 约束

- `comment_scores_business_pool_check` (CHECK)：`CHECK (business_pool::text = ANY (ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying]::text[]))`
- `comment_scores_comment_id_fkey` (FOREIGN KEY)：`FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE`
- `comment_scores_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `comment_scores_pkey`：`CREATE UNIQUE INDEX comment_scores_pkey ON public.comment_scores USING btree (id)`
- `idx_comment_scores_comment_latest`：`CREATE INDEX idx_comment_scores_comment_latest ON public.comment_scores USING btree (comment_id) WHERE (is_latest = true)`
- `idx_comment_scores_pool`：`CREATE INDEX idx_comment_scores_pool ON public.comment_scores USING btree (business_pool) WHERE (is_latest = true)`
- `idx_comment_scores_rule_version`：`CREATE INDEX idx_comment_scores_rule_version ON public.comment_scores USING btree (rule_version)`
- `ux_comment_scores_latest`：`CREATE UNIQUE INDEX ux_comment_scores_latest ON public.comment_scores USING btree (comment_id) WHERE (is_latest = true)`

## `comments`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('comments_id_seq'::regclass)` |
| `reddit_comment_id` | `character varying` | NO | `` |
| `source` | `character varying` | NO | `'reddit'::character varying` |
| `source_post_id` | `character varying` | NO | `` |
| `subreddit` | `character varying` | NO | `` |
| `parent_id` | `character varying` | YES | `` |
| `depth` | `integer` | NO | `0` |
| `body` | `text` | NO | `` |
| `author_id` | `character varying` | YES | `` |
| `author_name` | `character varying` | YES | `` |
| `author_created_utc` | `timestamp with time zone` | YES | `` |
| `created_utc` | `timestamp with time zone` | NO | `` |
| `score` | `integer` | NO | `0` |
| `is_submitter` | `boolean` | NO | `false` |
| `distinguished` | `character varying` | YES | `` |
| `edited` | `boolean` | NO | `false` |
| `permalink` | `text` | YES | `` |
| `removed_by_category` | `character varying` | YES | `` |
| `awards_count` | `integer` | NO | `0` |
| `captured_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `expires_at` | `timestamp with time zone` | YES | `` |
| `post_id` | `bigint` | NO | `` |
| `value_score` | `smallint` | YES | `` |
| `business_pool` | `character varying` | YES | `'lab'::character varying` |
| `is_deleted` | `boolean` | YES | `false` |
| `lang` | `character varying` | YES | `` |
| `source_track` | `character varying` | YES | `'incremental'::character varying` |
| `first_seen_at` | `timestamp with time zone` | YES | `now()` |
| `fetched_at` | `timestamp with time zone` | YES | `now()` |
| `crawl_run_id` | `uuid` | YES | `` |
| `community_run_id` | `uuid` | YES | `` |

### 约束

- `ck_comments_depth_nonneg` (CHECK)：`CHECK (depth >= 0)`
- `ck_comments_subreddit_format` (CHECK)：`CHECK (subreddit::text ~ '^r/[a-z0-9_]+$'::text)`
- `comments_business_pool_check` (CHECK)：`CHECK (business_pool::text = ANY (ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying]::text[]))`
- `comments_value_score_check` (CHECK)：`CHECK (value_score >= 0 AND value_score <= 10)`
- `fk_comments_posts_raw` (FOREIGN KEY)：`FOREIGN KEY (post_id) REFERENCES posts_raw(id) ON DELETE CASCADE`
- `pk_comments` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_comments_reddit_comment_id` (UNIQUE)：`UNIQUE (reddit_comment_id)`

### 索引

- `idx_comments_business_pool`：`CREATE INDEX idx_comments_business_pool ON public.comments USING btree (business_pool)`
- `idx_comments_captured_at`：`CREATE INDEX idx_comments_captured_at ON public.comments USING btree (captured_at)`
- `idx_comments_community_run_id`：`CREATE INDEX idx_comments_community_run_id ON public.comments USING btree (community_run_id) WHERE (community_run_id IS NOT NULL)`
- `idx_comments_crawl_run_id`：`CREATE INDEX idx_comments_crawl_run_id ON public.comments USING btree (crawl_run_id) WHERE (crawl_run_id IS NOT NULL)`
- `idx_comments_expires_at`：`CREATE INDEX idx_comments_expires_at ON public.comments USING btree (expires_at)`
- `idx_comments_parent_id`：`CREATE INDEX idx_comments_parent_id ON public.comments USING btree (parent_id)`
- `idx_comments_post_id`：`CREATE INDEX idx_comments_post_id ON public.comments USING btree (post_id)`
- `idx_comments_post_time`：`CREATE INDEX idx_comments_post_time ON public.comments USING btree (source, source_post_id, created_utc)`
- `idx_comments_subreddit_created`：`CREATE INDEX idx_comments_subreddit_created ON public.comments USING btree (subreddit, created_utc DESC)`
- `idx_comments_subreddit_time`：`CREATE INDEX idx_comments_subreddit_time ON public.comments USING btree (subreddit, created_utc)`
- `pk_comments`：`CREATE UNIQUE INDEX pk_comments ON public.comments USING btree (id)`
- `uq_comments_reddit_comment_id`：`CREATE UNIQUE INDEX uq_comments_reddit_comment_id ON public.comments USING btree (reddit_comment_id)`

## `community_audit`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('community_audit_id_seq'::regclass)` |
| `community_id` | `bigint` | NO | `` |
| `action` | `text` | NO | `` |
| `metrics` | `jsonb` | YES | `` |
| `reason` | `text` | YES | `` |
| `actor` | `text` | YES | `` |
| `created_at` | `timestamp with time zone` | YES | `now()` |

### 约束

- `community_audit_action_check` (CHECK)：`CHECK (action = ANY (ARRAY['promote'::text, 'demote'::text, 'blacklist'::text, 'restore'::text]))`
- `community_audit_community_id_fkey` (FOREIGN KEY)：`FOREIGN KEY (community_id) REFERENCES community_pool(id)`
- `community_audit_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `community_audit_pkey`：`CREATE UNIQUE INDEX community_audit_pkey ON public.community_audit USING btree (id)`
- `idx_community_audit_comm_time`：`CREATE INDEX idx_community_audit_comm_time ON public.community_audit USING btree (community_id, created_at DESC)`

## `community_cache`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `community_name` | `character varying` | NO | `` |
| `last_crawled_at` | `timestamp with time zone` | YES | `` |
| `ttl_seconds` | `integer` | NO | `3600` |
| `posts_cached` | `integer` | NO | `0` |
| `hit_count` | `integer` | NO | `0` |
| `last_hit_at` | `timestamp with time zone` | YES | `` |
| `crawl_priority` | `integer` | NO | `50` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `crawl_frequency_hours` | `integer` | NO | `2` |
| `is_active` | `boolean` | NO | `true` |
| `empty_hit` | `integer` | NO | `0` |
| `success_hit` | `integer` | NO | `0` |
| `failure_hit` | `integer` | NO | `0` |
| `avg_valid_posts` | `integer` | NO | `0` |
| `quality_tier` | `character varying` | NO | `` |
| `last_seen_post_id` | `character varying` | YES | `` |
| `last_seen_created_at` | `timestamp with time zone` | YES | `` |
| `total_posts_fetched` | `integer` | NO | `0` |
| `dedup_rate` | `numeric` | YES | `` |
| `member_count` | `integer` | YES | `` |
| `crawl_quality_score` | `numeric` | NO | `0.0` |
| `community_key` | `character varying` | NO | `` |
| `backfill_floor` | `timestamp with time zone` | YES | `` |
| `last_attempt_at` | `timestamp with time zone` | YES | `` |

### 约束

- `ck_cache_avg_valid_nonneg` (CHECK)：`CHECK (avg_valid_posts >= 0)`
- `ck_cache_empty_hit_nonneg` (CHECK)：`CHECK (empty_hit >= 0)`
- `ck_cache_failure_hit_nonneg` (CHECK)：`CHECK (failure_hit >= 0)`
- `ck_cache_quality_range` (CHECK)：`CHECK (crawl_quality_score >= 0::numeric AND crawl_quality_score <= 10::numeric)`
- `ck_cache_success_hit_nonneg` (CHECK)：`CHECK (success_hit >= 0)`
- `ck_cache_total_nonneg` (CHECK)：`CHECK (total_posts_fetched >= 0)`
- `ck_community_cache_ck_community_cache_name_format` (CHECK)：`CHECK (community_name::text ~ '^r/[a-zA-Z0-9_]+$'::text)`
- `ck_community_cache_hit_count_non_negative` (CHECK)：`CHECK (hit_count >= 0)`
- `ck_community_cache_member_count_nonneg` (CHECK)：`CHECK (member_count IS NULL OR member_count >= 0)`
- `ck_community_cache_name_format` (CHECK)：`CHECK (community_name::text ~ '^r/[a-zA-Z0-9_]+$'::text)`
- `ck_community_cache_posts_non_negative` (CHECK)：`CHECK (posts_cached >= 0)`
- `ck_community_cache_priority_range` (CHECK)：`CHECK (crawl_priority >= 1 AND crawl_priority <= 100)`
- `ck_community_cache_ttl_positive` (CHECK)：`CHECK (ttl_seconds > 0)`
- `pk_community_cache_name` (PRIMARY KEY)：`PRIMARY KEY (community_name)`

### 索引

- `pk_community_cache_name`：`CREATE UNIQUE INDEX pk_community_cache_name ON public.community_cache USING btree (community_name)`

## `community_category_map`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `community_id` | `integer` | NO | `` |
| `category_key` | `character varying` | NO | `` |
| `is_primary` | `boolean` | YES | `false` |
| `created_at` | `timestamp with time zone` | YES | `now()` |

### 约束

- `fk_map_category` (FOREIGN KEY)：`FOREIGN KEY (category_key) REFERENCES business_categories(key) ON DELETE CASCADE`
- `fk_map_community` (FOREIGN KEY)：`FOREIGN KEY (community_id) REFERENCES community_pool(id) ON DELETE CASCADE`
- `community_category_map_pkey` (PRIMARY KEY)：`PRIMARY KEY (community_id, category_key)`

### 索引

- `community_category_map_pkey`：`CREATE UNIQUE INDEX community_category_map_pkey ON public.community_category_map USING btree (community_id, category_key)`

## `community_import_history`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('community_import_history_id_seq'::regclass)` |
| `filename` | `character varying` | NO | `` |
| `uploaded_by` | `character varying` | NO | `` |
| `uploaded_by_user_id` | `uuid` | YES | `` |
| `dry_run` | `boolean` | NO | `false` |
| `status` | `character varying` | NO | `` |
| `total_rows` | `integer` | NO | `0` |
| `valid_rows` | `integer` | NO | `0` |
| `invalid_rows` | `integer` | NO | `0` |
| `duplicate_rows` | `integer` | NO | `0` |
| `imported_rows` | `integer` | NO | `0` |
| `error_details` | `jsonb` | YES | `` |
| `summary_preview` | `jsonb` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `created_by` | `uuid` | YES | `` |
| `updated_by` | `uuid` | YES | `` |

### 约束

- `fk_community_import_history_created_by` (FOREIGN KEY)：`FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_community_import_history_updated_by` (FOREIGN KEY)：`FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_community_import_history_uploaded_by_user_id` (FOREIGN KEY)：`FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- `community_import_history_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `community_import_history_pkey`：`CREATE UNIQUE INDEX community_import_history_pkey ON public.community_import_history USING btree (id)`
- `idx_community_import_history_created`：`CREATE INDEX idx_community_import_history_created ON public.community_import_history USING btree (created_at)`
- `idx_community_import_history_uploaded_by`：`CREATE INDEX idx_community_import_history_uploaded_by ON public.community_import_history USING btree (uploaded_by_user_id)`

## `community_pool`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('community_pool_id_seq'::regclass)` |
| `name` | `character varying` | NO | `` |
| `tier` | `character varying` | NO | `` |
| `categories` | `jsonb` | NO | `` |
| `description_keywords` | `jsonb` | NO | `` |
| `daily_posts` | `integer` | NO | `0` |
| `avg_comment_length` | `integer` | NO | `0` |
| `user_feedback_count` | `integer` | NO | `0` |
| `discovered_count` | `integer` | NO | `0` |
| `is_active` | `boolean` | NO | `true` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `priority` | `character varying` | NO | `'medium'::character varying` |
| `is_blacklisted` | `boolean` | NO | `false` |
| `blacklist_reason` | `character varying` | YES | `` |
| `downrank_factor` | `numeric` | YES | `` |
| `created_by` | `uuid` | YES | `` |
| `updated_by` | `uuid` | YES | `` |
| `deleted_at` | `timestamp with time zone` | YES | `` |
| `deleted_by` | `uuid` | YES | `` |
| `semantic_quality_score` | `numeric` | NO | `` |
| `health_status` | `character varying` | NO | `'unknown'::character varying` |
| `last_evaluated_at` | `timestamp with time zone` | YES | `` |
| `auto_tier_enabled` | `boolean` | NO | `false` |
| `name_key` | `character varying` | NO | `` |
| `status` | `character varying` | YES | `'active'::character varying` |
| `core_post_ratio` | `numeric` | YES | `0` |
| `avg_value_score` | `numeric` | YES | `0` |
| `recent_core_posts_30d` | `integer` | YES | `0` |
| `stats_updated_at` | `timestamp with time zone` | YES | `` |
| `vertical` | `character varying` | YES | `` |
| `history_depth_months` | `integer` | YES | `24` |
| `min_posts_target` | `integer` | YES | `3000` |

### 约束

- `ck_community_pool_ck_community_pool_name_format` (CHECK)：`CHECK (name::text ~ '^r/[a-zA-Z0-9_]+$'::text)`
- `ck_community_pool_name_format` (CHECK)：`CHECK (name::text ~ '^r/[a-z0-9_]+$'::text)`
- `ck_community_pool_name_len` (CHECK)：`CHECK (char_length(name::text) >= 3 AND char_length(name::text) <= 100)`
- `ck_community_pool_status` (CHECK)：`CHECK (status::text = ANY (ARRAY['active'::character varying, 'lab'::character varying, 'paused'::character varying, 'candidate'::character varying, 'banned'::character varying]::text[]))`
- `ck_pool_categories_jsonb` (CHECK)：`CHECK (categories IS NULL OR (jsonb_typeof(categories) = ANY (ARRAY['array'::text, 'object'::text]))) NOT VALID`
- `ck_pool_keywords_jsonb` (CHECK)：`CHECK (description_keywords IS NULL OR (jsonb_typeof(description_keywords) = ANY (ARRAY['array'::text, 'object'::text]))) NOT VALID`
- `fk_community_pool_created_by` (FOREIGN KEY)：`FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_community_pool_deleted_by` (FOREIGN KEY)：`FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_community_pool_updated_by` (FOREIGN KEY)：`FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- `pk_community_pool` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_community_pool_name` (UNIQUE)：`UNIQUE (name)`

### 索引

- `idx_community_pool_categories_gin`：`CREATE INDEX idx_community_pool_categories_gin ON public.community_pool USING gin (categories)`
- `idx_community_pool_deleted_at`：`CREATE INDEX idx_community_pool_deleted_at ON public.community_pool USING btree (deleted_at)`
- `idx_community_pool_is_active`：`CREATE INDEX idx_community_pool_is_active ON public.community_pool USING btree (is_active)`
- `idx_community_pool_name_key`：`CREATE INDEX idx_community_pool_name_key ON public.community_pool USING btree (name_key)`
- `idx_community_pool_tier`：`CREATE INDEX idx_community_pool_tier ON public.community_pool USING btree (tier)`
- `pk_community_pool`：`CREATE UNIQUE INDEX pk_community_pool ON public.community_pool USING btree (id)`
- `uq_community_pool_name`：`CREATE UNIQUE INDEX uq_community_pool_name ON public.community_pool USING btree (name)`

## `community_roles_map`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `subreddit` | `character varying` | NO | `` |
| `role` | `character varying` | YES | `` |

### 约束

- `community_roles_map_pkey` (PRIMARY KEY)：`PRIMARY KEY (subreddit)`

### 索引

- `community_roles_map_pkey`：`CREATE UNIQUE INDEX community_roles_map_pkey ON public.community_roles_map USING btree (subreddit)`

## `content_entities`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('content_entities_id_seq'::regclass)` |
| `content_type` | `character varying` | NO | `` |
| `content_id` | `bigint` | NO | `` |
| `entity` | `character varying` | NO | `` |
| `entity_type` | `character varying` | NO | `'other'::character varying` |
| `count` | `integer` | NO | `1` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `source_model` | `character varying` | YES | `'unknown'::character varying` |
| `feature_version` | `integer` | YES | `1` |

### 约束

- `pk_content_entities` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_content_entities_entity`：`CREATE INDEX idx_content_entities_entity ON public.content_entities USING btree (entity, entity_type)`
- `idx_content_entities_target`：`CREATE INDEX idx_content_entities_target ON public.content_entities USING btree (content_type, content_id)`
- `pk_content_entities`：`CREATE UNIQUE INDEX pk_content_entities ON public.content_entities USING btree (id)`

## `content_labels`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('content_labels_id_seq'::regclass)` |
| `content_type` | `character varying` | NO | `` |
| `content_id` | `bigint` | NO | `` |
| `category` | `character varying` | NO | `` |
| `aspect` | `character varying` | NO | `'other'::character varying` |
| `confidence` | `integer` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `sentiment_score` | `double precision` | YES | `` |
| `sentiment_label` | `character varying` | YES | `` |
| `source_model` | `character varying` | YES | `'unknown'::character varying` |
| `feature_version` | `integer` | YES | `1` |

### 约束

- `pk_content_labels` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_content_labels_cat_aspect`：`CREATE INDEX idx_content_labels_cat_aspect ON public.content_labels USING btree (category, aspect)`
- `idx_content_labels_sentiment`：`CREATE INDEX idx_content_labels_sentiment ON public.content_labels USING btree (sentiment_score)`
- `idx_content_labels_target`：`CREATE INDEX idx_content_labels_target ON public.content_labels USING btree (content_type, content_id)`
- `pk_content_labels`：`CREATE UNIQUE INDEX pk_content_labels ON public.content_labels USING btree (id)`

## `crawl_metrics`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('crawl_metrics_id_seq'::regclass)` |
| `metric_date` | `date` | NO | `` |
| `metric_hour` | `integer` | NO | `` |
| `cache_hit_rate` | `numeric` | NO | `` |
| `valid_posts_24h` | `integer` | NO | `` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `total_communities` | `integer` | NO | `` |
| `successful_crawls` | `integer` | NO | `` |
| `empty_crawls` | `integer` | NO | `` |
| `failed_crawls` | `integer` | NO | `` |
| `avg_latency_seconds` | `numeric` | NO | `` |
| `total_new_posts` | `integer` | NO | `` |
| `total_updated_posts` | `integer` | NO | `` |
| `total_duplicates` | `integer` | NO | `` |
| `tier_assignments` | `json` | YES | `` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `crawl_run_id` | `uuid` | YES | `` |

### 约束

- `pk_crawl_metrics` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_crawl_metrics_date_hour` (UNIQUE)：`UNIQUE (metric_date, metric_hour)`

### 索引

- `idx_crawl_metrics_crawl_run_id`：`CREATE INDEX idx_crawl_metrics_crawl_run_id ON public.crawl_metrics USING btree (crawl_run_id) WHERE (crawl_run_id IS NOT NULL)`
- `idx_metrics_metric_date`：`CREATE INDEX idx_metrics_metric_date ON public.crawl_metrics USING btree (metric_date)`
- `idx_metrics_metric_hour`：`CREATE INDEX idx_metrics_metric_hour ON public.crawl_metrics USING btree (metric_hour)`
- `pk_crawl_metrics`：`CREATE UNIQUE INDEX pk_crawl_metrics ON public.crawl_metrics USING btree (id)`
- `uq_crawl_metrics_date_hour`：`CREATE UNIQUE INDEX uq_crawl_metrics_date_hour ON public.crawl_metrics USING btree (metric_date, metric_hour)`

## `crawler_run_targets`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `` |
| `crawl_run_id` | `uuid` | NO | `` |
| `subreddit` | `text` | NO | `` |
| `started_at` | `timestamp with time zone` | NO | `now()` |
| `completed_at` | `timestamp with time zone` | YES | `` |
| `status` | `character varying` | NO | `'running'::character varying` |
| `config` | `jsonb` | NO | `'{}'::jsonb` |
| `metrics` | `jsonb` | NO | `'{}'::jsonb` |
| `error_code` | `character varying` | YES | `` |
| `error_message_short` | `text` | YES | `` |
| `plan_kind` | `character varying` | YES | `` |
| `idempotency_key` | `text` | YES | `` |
| `idempotency_key_human` | `text` | YES | `` |

### 约束

- `fk_crawler_run_targets_crawl_run_id_crawler_runs` (FOREIGN KEY)：`FOREIGN KEY (crawl_run_id) REFERENCES crawler_runs(id) ON DELETE CASCADE`
- `pk_crawler_run_targets` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_crawler_run_targets_crawl_run_id`：`CREATE INDEX idx_crawler_run_targets_crawl_run_id ON public.crawler_run_targets USING btree (crawl_run_id)`
- `idx_crawler_run_targets_plan_kind`：`CREATE INDEX idx_crawler_run_targets_plan_kind ON public.crawler_run_targets USING btree (plan_kind) WHERE (plan_kind IS NOT NULL)`
- `idx_crawler_run_targets_started_at`：`CREATE INDEX idx_crawler_run_targets_started_at ON public.crawler_run_targets USING btree (started_at)`
- `idx_crawler_run_targets_status`：`CREATE INDEX idx_crawler_run_targets_status ON public.crawler_run_targets USING btree (status)`
- `idx_crawler_run_targets_subreddit`：`CREATE INDEX idx_crawler_run_targets_subreddit ON public.crawler_run_targets USING btree (subreddit)`
- `pk_crawler_run_targets`：`CREATE UNIQUE INDEX pk_crawler_run_targets ON public.crawler_run_targets USING btree (id)`
- `uq_crawler_run_targets_run_idempotency_key`：`CREATE UNIQUE INDEX uq_crawler_run_targets_run_idempotency_key ON public.crawler_run_targets USING btree (crawl_run_id, idempotency_key) WHERE (idempotency_key IS NOT NULL)`

## `crawler_runs`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `` |
| `started_at` | `timestamp with time zone` | NO | `now()` |
| `completed_at` | `timestamp with time zone` | YES | `` |
| `status` | `character varying` | NO | `'running'::character varying` |
| `config` | `jsonb` | NO | `'{}'::jsonb` |
| `metrics` | `jsonb` | NO | `'{}'::jsonb` |

### 约束

- `pk_crawler_runs` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_crawler_runs_started_at`：`CREATE INDEX idx_crawler_runs_started_at ON public.crawler_runs USING btree (started_at)`
- `idx_crawler_runs_status`：`CREATE INDEX idx_crawler_runs_status ON public.crawler_runs USING btree (status)`
- `pk_crawler_runs`：`CREATE UNIQUE INDEX pk_crawler_runs ON public.crawler_runs USING btree (id)`

## `data_audit_events`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('data_audit_events_id_seq'::regclass)` |
| `event_type` | `character varying` | NO | `` |
| `target_type` | `character varying` | NO | `` |
| `target_id` | `character varying` | NO | `` |
| `old_value` | `jsonb` | YES | `` |
| `new_value` | `jsonb` | YES | `` |
| `reason` | `text` | YES | `` |
| `source_component` | `character varying` | YES | `` |
| `created_at` | `timestamp with time zone` | YES | `now()` |

### 约束

- `data_audit_events_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `data_audit_events_pkey`：`CREATE UNIQUE INDEX data_audit_events_pkey ON public.data_audit_events USING btree (id)`
- `idx_data_audit_created`：`CREATE INDEX idx_data_audit_created ON public.data_audit_events USING btree (created_at DESC)`
- `idx_data_audit_event`：`CREATE INDEX idx_data_audit_event ON public.data_audit_events USING btree (event_type)`
- `idx_data_audit_target`：`CREATE INDEX idx_data_audit_target ON public.data_audit_events USING btree (target_type, target_id)`

## `discovered_communities`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('discovered_communities_id_seq'::regclass)` |
| `name` | `character varying` | NO | `` |
| `discovered_from_keywords` | `jsonb` | YES | `` |
| `discovered_count` | `integer` | NO | `1` |
| `first_discovered_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `last_discovered_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `status` | `character varying` | NO | `'pending'::character varying` |
| `admin_reviewed_at` | `timestamp with time zone` | YES | `` |
| `admin_notes` | `text` | YES | `` |
| `discovered_from_task_id` | `uuid` | YES | `` |
| `reviewed_by` | `uuid` | YES | `` |
| `created_by` | `uuid` | YES | `` |
| `updated_by` | `uuid` | YES | `` |
| `deleted_at` | `timestamp with time zone` | YES | `` |
| `deleted_by` | `uuid` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `metrics` | `jsonb` | NO | `'{}'::jsonb` |
| `tags` | `ARRAY` | NO | `'{}'::character varying[]` |
| `cooldown_until` | `timestamp with time zone` | YES | `` |
| `rejection_count` | `integer` | NO | `0` |

### 约束

- `ck_pending_communities_ck_pending_communities_name_format` (CHECK)：`CHECK (name::text ~ '^r/[a-zA-Z0-9_]+$'::text)`
- `ck_pending_communities_ck_pending_communities_name_len` (CHECK)：`CHECK (char_length(name::text) >= 3 AND char_length(name::text) <= 100)`
- `ck_pending_communities_name_format` (CHECK)：`CHECK (name::text ~ '^r/[a-zA-Z0-9_]+$'::text)`
- `fk_discovered_communities_created_by` (FOREIGN KEY)：`FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_discovered_communities_deleted_by` (FOREIGN KEY)：`FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_discovered_communities_discovered_from_task_id_tasks` (FOREIGN KEY)：`FOREIGN KEY (discovered_from_task_id) REFERENCES tasks(id) ON DELETE SET NULL`
- `fk_discovered_communities_reviewed_by` (FOREIGN KEY)：`FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_discovered_communities_updated_by` (FOREIGN KEY)：`FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_discovered_to_pool` (FOREIGN KEY)：`FOREIGN KEY (name) REFERENCES community_pool(name) ON DELETE SET NULL`
- `fk_pending_communities_task_id` (FOREIGN KEY)：`FOREIGN KEY (discovered_from_task_id) REFERENCES tasks(id) ON DELETE SET NULL`
- `pk_pending_communities` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_pending_communities_name` (UNIQUE)：`UNIQUE (name)`

### 索引

- `idx_discovered_communities_cooldown`：`CREATE INDEX idx_discovered_communities_cooldown ON public.discovered_communities USING btree (cooldown_until) WHERE (cooldown_until IS NOT NULL)`
- `idx_discovered_communities_deleted_at`：`CREATE INDEX idx_discovered_communities_deleted_at ON public.discovered_communities USING btree (deleted_at)`
- `idx_discovered_communities_discovered_count`：`CREATE INDEX idx_discovered_communities_discovered_count ON public.discovered_communities USING btree (discovered_count)`
- `idx_discovered_communities_reviewed_by`：`CREATE INDEX idx_discovered_communities_reviewed_by ON public.discovered_communities USING btree (reviewed_by)`
- `idx_discovered_communities_status`：`CREATE INDEX idx_discovered_communities_status ON public.discovered_communities USING btree (status)`
- `idx_discovered_communities_task_id`：`CREATE INDEX idx_discovered_communities_task_id ON public.discovered_communities USING btree (discovered_from_task_id)`
- `pk_pending_communities`：`CREATE UNIQUE INDEX pk_pending_communities ON public.discovered_communities USING btree (id)`
- `uq_pending_communities_name`：`CREATE UNIQUE INDEX uq_pending_communities_name ON public.discovered_communities USING btree (name)`

## `evidence_posts`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('evidence_posts_id_seq'::regclass)` |
| `crawl_run_id` | `uuid` | YES | `` |
| `target_id` | `uuid` | YES | `` |
| `probe_source` | `character varying` | NO | `` |
| `source_query` | `text` | YES | `` |
| `source_query_hash` | `character varying` | NO | `` |
| `source_post_id` | `character varying` | NO | `` |
| `subreddit` | `character varying` | NO | `` |
| `title` | `text` | NO | `` |
| `summary` | `text` | YES | `` |
| `score` | `integer` | NO | `0` |
| `num_comments` | `integer` | NO | `0` |
| `post_created_at` | `timestamp with time zone` | YES | `` |
| `evidence_score` | `integer` | NO | `0` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |

### 约束

- `fk_evidence_posts_crawl_run_id_crawler_runs` (FOREIGN KEY)：`FOREIGN KEY (crawl_run_id) REFERENCES crawler_runs(id) ON DELETE SET NULL`
- `fk_evidence_posts_target_id_crawler_run_targets` (FOREIGN KEY)：`FOREIGN KEY (target_id) REFERENCES crawler_run_targets(id) ON DELETE SET NULL`
- `pk_evidence_posts` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_evidence_posts_probe_query_post` (UNIQUE)：`UNIQUE (probe_source, source_query_hash, source_post_id)`

### 索引

- `idx_evidence_posts_crawl_run_id`：`CREATE INDEX idx_evidence_posts_crawl_run_id ON public.evidence_posts USING btree (crawl_run_id)`
- `idx_evidence_posts_probe_query`：`CREATE INDEX idx_evidence_posts_probe_query ON public.evidence_posts USING btree (probe_source, source_query_hash)`
- `idx_evidence_posts_subreddit_created`：`CREATE INDEX idx_evidence_posts_subreddit_created ON public.evidence_posts USING btree (subreddit, created_at)`
- `idx_evidence_posts_target_id`：`CREATE INDEX idx_evidence_posts_target_id ON public.evidence_posts USING btree (target_id)`
- `pk_evidence_posts`：`CREATE UNIQUE INDEX pk_evidence_posts ON public.evidence_posts USING btree (id)`
- `uq_evidence_posts_probe_query_post`：`CREATE UNIQUE INDEX uq_evidence_posts_probe_query_post ON public.evidence_posts USING btree (probe_source, source_query_hash, source_post_id)`

## `evidences`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `` |
| `insight_card_id` | `uuid` | NO | `` |
| `post_url` | `character varying` | NO | `` |
| `excerpt` | `text` | NO | `` |
| `timestamp` | `timestamp with time zone` | NO | `` |
| `subreddit` | `character varying` | NO | `` |
| `score` | `numeric` | NO | `0.0` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |

### 约束

- `ck_evidences_score_range` (CHECK)：`CHECK (score >= 0.0 AND score <= 1.0)`
- `fk_evidences_insight_card_id_insight_cards` (FOREIGN KEY)：`FOREIGN KEY (insight_card_id) REFERENCES insight_cards(id) ON DELETE CASCADE`
- `pk_evidences` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_evidences_insight_card_id`：`CREATE INDEX idx_evidences_insight_card_id ON public.evidences USING btree (insight_card_id)`
- `idx_evidences_score`：`CREATE INDEX idx_evidences_score ON public.evidences USING btree (score)`
- `idx_evidences_subreddit`：`CREATE INDEX idx_evidences_subreddit ON public.evidences USING btree (subreddit)`
- `idx_evidences_timestamp`：`CREATE INDEX idx_evidences_timestamp ON public.evidences USING btree ("timestamp")`
- `pk_evidences`：`CREATE UNIQUE INDEX pk_evidences ON public.evidences USING btree (id)`

## `facts_quality_audit`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `run_id` | `uuid` | NO | `` |
| `topic` | `text` | NO | `` |
| `days` | `integer` | NO | `` |
| `mode` | `text` | NO | `` |
| `config_hash` | `text` | YES | `` |
| `trend_source` | `text` | YES | `` |
| `trend_degraded` | `boolean` | YES | `` |
| `time_window_used` | `integer` | YES | `` |
| `comments_count` | `integer` | YES | `` |
| `posts_count` | `integer` | YES | `` |
| `solutions_count` | `integer` | YES | `` |
| `community_coverage` | `integer` | YES | `` |
| `degraded` | `boolean` | YES | `` |
| `data_fallback` | `boolean` | YES | `` |
| `posts_fallback` | `boolean` | YES | `` |
| `solutions_fallback` | `boolean` | YES | `` |
| `dynamic_whitelist` | `jsonb` | YES | `` |
| `dynamic_blacklist` | `jsonb` | YES | `` |
| `insufficient_flags` | `jsonb` | YES | `` |
| `created_at` | `timestamp with time zone` | YES | `now()` |

### 约束

- `facts_quality_audit_pkey` (PRIMARY KEY)：`PRIMARY KEY (run_id)`

### 索引

- `facts_quality_audit_pkey`：`CREATE UNIQUE INDEX facts_quality_audit_pkey ON public.facts_quality_audit USING btree (run_id)`
- `idx_facts_quality_created_at`：`CREATE INDEX idx_facts_quality_created_at ON public.facts_quality_audit USING btree (created_at DESC)`

## `facts_run_logs`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `` |
| `task_id` | `uuid` | NO | `` |
| `audit_level` | `character varying` | NO | `'lab'::character varying` |
| `status` | `character varying` | NO | `'ok'::character varying` |
| `validator_level` | `character varying` | NO | `'info'::character varying` |
| `retention_days` | `integer` | NO | `7` |
| `expires_at` | `timestamp with time zone` | YES | `` |
| `summary` | `jsonb` | NO | `'{}'::jsonb` |
| `error_code` | `character varying` | YES | `` |
| `error_message_short` | `text` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |

### 约束

- `ck_facts_run_logs_ck_facts_run_logs_valid_audit_level` (CHECK)：`CHECK (audit_level::text = ANY (ARRAY['gold'::character varying, 'lab'::character varying, 'noise'::character varying]::text[]))`
- `ck_facts_run_logs_ck_facts_run_logs_valid_status` (CHECK)：`CHECK (status::text = ANY (ARRAY['ok'::character varying, 'blocked'::character varying, 'failed'::character varying, 'skipped'::character varying]::text[]))`
- `ck_facts_run_logs_ck_facts_run_logs_valid_validator_level` (CHECK)：`CHECK (validator_level::text = ANY (ARRAY['info'::character varying, 'warn'::character varying, 'error'::character varying]::text[]))`
- `fk_facts_run_logs_task_id_tasks` (FOREIGN KEY)：`FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE`
- `pk_facts_run_logs` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_facts_run_logs_audit_level`：`CREATE INDEX idx_facts_run_logs_audit_level ON public.facts_run_logs USING btree (audit_level)`
- `idx_facts_run_logs_created_at`：`CREATE INDEX idx_facts_run_logs_created_at ON public.facts_run_logs USING btree (created_at)`
- `idx_facts_run_logs_expires_at`：`CREATE INDEX idx_facts_run_logs_expires_at ON public.facts_run_logs USING btree (expires_at)`
- `idx_facts_run_logs_status`：`CREATE INDEX idx_facts_run_logs_status ON public.facts_run_logs USING btree (status)`
- `idx_facts_run_logs_task_id`：`CREATE INDEX idx_facts_run_logs_task_id ON public.facts_run_logs USING btree (task_id)`
- `pk_facts_run_logs`：`CREATE UNIQUE INDEX pk_facts_run_logs ON public.facts_run_logs USING btree (id)`

## `facts_snapshots`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `` |
| `task_id` | `uuid` | NO | `` |
| `schema_version` | `character varying` | NO | `'2.0'::character varying` |
| `v2_package` | `jsonb` | NO | `'{}'::jsonb` |
| `quality` | `jsonb` | NO | `'{}'::jsonb` |
| `passed` | `boolean` | NO | `false` |
| `tier` | `character varying` | NO | `'C_scouting'::character varying` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |
| `audit_level` | `character varying` | NO | `'lab'::character varying` |
| `status` | `character varying` | NO | `'ok'::character varying` |
| `validator_level` | `character varying` | NO | `'info'::character varying` |
| `retention_days` | `integer` | NO | `30` |
| `expires_at` | `timestamp with time zone` | YES | `` |
| `blocked_reason` | `character varying` | YES | `` |
| `error_code` | `character varying` | YES | `` |

### 约束

- `ck_facts_snapshots_ck_facts_snapshots_schema_version_non_empty` (CHECK)：`CHECK (schema_version::text <> ''::text)`
- `ck_facts_snapshots_ck_facts_snapshots_valid_audit_level` (CHECK)：`CHECK (audit_level::text = ANY (ARRAY['gold'::character varying, 'lab'::character varying, 'noise'::character varying]::text[]))`
- `ck_facts_snapshots_ck_facts_snapshots_valid_status` (CHECK)：`CHECK (status::text = ANY (ARRAY['ok'::character varying, 'blocked'::character varying, 'failed'::character varying]::text[]))`
- `ck_facts_snapshots_ck_facts_snapshots_valid_tier` (CHECK)：`CHECK (tier::text = ANY (ARRAY['A_full'::character varying, 'B_trimmed'::character varying, 'C_scouting'::character varying, 'X_blocked'::character varying]::text[]))`
- `ck_facts_snapshots_ck_facts_snapshots_valid_validator_level` (CHECK)：`CHECK (validator_level::text = ANY (ARRAY['info'::character varying, 'warn'::character varying, 'error'::character varying]::text[]))`
- `fk_facts_snapshots_task_id_tasks` (FOREIGN KEY)：`FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE`
- `pk_facts_snapshots` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_facts_snapshots_audit_level`：`CREATE INDEX idx_facts_snapshots_audit_level ON public.facts_snapshots USING btree (audit_level)`
- `idx_facts_snapshots_created_at`：`CREATE INDEX idx_facts_snapshots_created_at ON public.facts_snapshots USING btree (created_at)`
- `idx_facts_snapshots_expires_at`：`CREATE INDEX idx_facts_snapshots_expires_at ON public.facts_snapshots USING btree (expires_at)`
- `idx_facts_snapshots_passed`：`CREATE INDEX idx_facts_snapshots_passed ON public.facts_snapshots USING btree (passed)`
- `idx_facts_snapshots_status`：`CREATE INDEX idx_facts_snapshots_status ON public.facts_snapshots USING btree (status)`
- `idx_facts_snapshots_task_created`：`CREATE INDEX idx_facts_snapshots_task_created ON public.facts_snapshots USING btree (task_id, created_at)`
- `idx_facts_snapshots_task_id`：`CREATE INDEX idx_facts_snapshots_task_id ON public.facts_snapshots USING btree (task_id)`
- `idx_facts_snapshots_tier`：`CREATE INDEX idx_facts_snapshots_tier ON public.facts_snapshots USING btree (tier)`
- `pk_facts_snapshots`：`CREATE UNIQUE INDEX pk_facts_snapshots ON public.facts_snapshots USING btree (id)`

## `feedback_events`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `source` | `text` | NO | `` |
| `event_type` | `text` | NO | `` |
| `user_id` | `text` | YES | `` |
| `task_id` | `text` | YES | `` |
| `analysis_id` | `text` | YES | `` |
| `payload` | `jsonb` | NO | `` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |

### 约束

- `ck_feedback_event_type` (CHECK)：`CHECK (event_type = ANY (ARRAY['community_decision'::text, 'analysis_rating'::text, 'insight_flag'::text, 'metric'::text]))`
- `ck_feedback_source` (CHECK)：`CHECK (source = ANY (ARRAY['user'::text, 'admin'::text, 'system'::text]))`
- `feedback_events_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `feedback_events_pkey`：`CREATE UNIQUE INDEX feedback_events_pkey ON public.feedback_events USING btree (id)`
- `ix_feedback_events_task`：`CREATE INDEX ix_feedback_events_task ON public.feedback_events USING btree (task_id)`
- `ix_feedback_events_type_time`：`CREATE INDEX ix_feedback_events_type_time ON public.feedback_events USING btree (event_type, created_at)`

## `insight_cards`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `` |
| `task_id` | `uuid` | NO | `` |
| `title` | `character varying` | NO | `` |
| `summary` | `text` | NO | `` |
| `confidence` | `numeric` | NO | `` |
| `time_window_days` | `integer` | NO | `30` |
| `subreddits` | `ARRAY` | NO | `'{}'::character varying[]` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |

### 约束

- `ck_insight_cards_ck_insight_cards_confidence_range` (CHECK)：`CHECK (confidence >= 0.0 AND confidence <= 1.0)`
- `ck_insight_cards_ck_insight_cards_time_window_positive` (CHECK)：`CHECK (time_window_days > 0)`
- `fk_insight_cards_task_id_tasks` (FOREIGN KEY)：`FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE`
- `pk_insight_cards` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_insight_cards_task_title` (UNIQUE)：`UNIQUE (task_id, title)`

### 索引

- `idx_insight_cards_confidence`：`CREATE INDEX idx_insight_cards_confidence ON public.insight_cards USING btree (confidence)`
- `idx_insight_cards_created_at`：`CREATE INDEX idx_insight_cards_created_at ON public.insight_cards USING btree (created_at)`
- `idx_insight_cards_subreddits_gin`：`CREATE INDEX idx_insight_cards_subreddits_gin ON public.insight_cards USING gin (subreddits)`
- `idx_insight_cards_task_id`：`CREATE INDEX idx_insight_cards_task_id ON public.insight_cards USING btree (task_id)`
- `pk_insight_cards`：`CREATE UNIQUE INDEX pk_insight_cards ON public.insight_cards USING btree (id)`
- `uq_insight_cards_task_title`：`CREATE UNIQUE INDEX uq_insight_cards_task_title ON public.insight_cards USING btree (task_id, title)`

## `maintenance_audit`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('maintenance_audit_id_seq'::regclass)` |
| `task_name` | `character varying` | NO | `` |
| `source` | `character varying` | YES | `` |
| `triggered_by` | `character varying` | YES | `` |
| `started_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `ended_at` | `timestamp with time zone` | YES | `` |
| `affected_rows` | `integer` | NO | `0` |
| `sample_ids` | `ARRAY` | YES | `` |
| `extra` | `jsonb` | YES | `` |

### 约束

- `pk_maintenance_audit` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_maintenance_audit_started`：`CREATE INDEX idx_maintenance_audit_started ON public.maintenance_audit USING btree (started_at)`
- `idx_maintenance_audit_task`：`CREATE INDEX idx_maintenance_audit_task ON public.maintenance_audit USING btree (task_name)`
- `pk_maintenance_audit`：`CREATE UNIQUE INDEX pk_maintenance_audit ON public.maintenance_audit USING btree (id)`

## `noise_labels`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('noise_labels_id_seq'::regclass)` |
| `content_type` | `text` | NO | `` |
| `content_id` | `bigint` | NO | `` |
| `noise_type` | `text` | NO | `` |
| `reason` | `text` | YES | `` |
| `created_at` | `timestamp with time zone` | YES | `now()` |

### 约束

- `noise_labels_content_type_check` (CHECK)：`CHECK (content_type = ANY (ARRAY['post'::text, 'comment'::text]))`
- `noise_labels_noise_type_check` (CHECK)：`CHECK (noise_type = ANY (ARRAY['employee_rant'::text, 'resale'::text, 'bot'::text, 'automod'::text, 'template'::text, 'spam_manual'::text, 'offtopic'::text, 'low_quality'::text, 'pure_social'::text, 'rage_rant'::text, 'meme_only'::text, 'ultra_short'::text]))`
- `noise_labels_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_noise_labels_target`：`CREATE INDEX idx_noise_labels_target ON public.noise_labels USING btree (noise_type, content_type, content_id)`
- `noise_labels_pkey`：`CREATE UNIQUE INDEX noise_labels_pkey ON public.noise_labels USING btree (id)`

## `post_embeddings`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `post_id` | `bigint` | NO | `` |
| `model_version` | `character varying` | NO | `'BAAI/bge-m3'::character varying` |
| `embedding` | `USER-DEFINED` | YES | `` |
| `created_at` | `timestamp with time zone` | YES | `now()` |
| `source_model` | `character varying` | YES | `'BAAI/bge-m3'::character varying` |
| `feature_version` | `integer` | YES | `1` |

### 约束

- `fk_embeddings_post` (FOREIGN KEY)：`FOREIGN KEY (post_id) REFERENCES posts_raw(id) ON DELETE CASCADE`
- `pk_post_embeddings` (PRIMARY KEY)：`PRIMARY KEY (post_id, model_version)`

### 索引

- `idx_post_embeddings_hnsw`：`CREATE INDEX idx_post_embeddings_hnsw ON public.post_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='128')`
- `idx_post_embeddings_post_id`：`CREATE INDEX idx_post_embeddings_post_id ON public.post_embeddings USING btree (post_id)`
- `pk_post_embeddings`：`CREATE UNIQUE INDEX pk_post_embeddings ON public.post_embeddings USING btree (post_id, model_version)`

## `post_scores`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `post_id` | `bigint` | NO | `` |
| `llm_version` | `character varying` | NO | `` |
| `rule_version` | `character varying` | NO | `` |
| `scored_at` | `timestamp with time zone` | YES | `now()` |
| `is_latest` | `boolean` | YES | `true` |
| `value_score` | `numeric` | YES | `` |
| `opportunity_score` | `numeric` | YES | `` |
| `business_pool` | `character varying` | YES | `` |
| `sentiment` | `numeric` | YES | `` |
| `purchase_intent_score` | `numeric` | YES | `` |
| `tags_analysis` | `jsonb` | YES | `'{}'::jsonb` |
| `entities_extracted` | `jsonb` | YES | `'[]'::jsonb` |
| `calculation_log` | `jsonb` | YES | `'{}'::jsonb` |

### 约束

- `post_scores_business_pool_check` (CHECK)：`CHECK (business_pool::text = ANY (ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying]::text[]))`
- `post_scores_post_id_fkey` (FOREIGN KEY)：`FOREIGN KEY (post_id) REFERENCES posts_raw(id) ON DELETE CASCADE`
- `post_scores_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_post_scores_pool`：`CREATE INDEX idx_post_scores_pool ON public.post_scores USING btree (business_pool) WHERE (is_latest = true)`
- `idx_post_scores_post_id_full`：`CREATE INDEX idx_post_scores_post_id_full ON public.post_scores USING btree (post_id)`
- `idx_post_scores_post_latest`：`CREATE INDEX idx_post_scores_post_latest ON public.post_scores USING btree (post_id) WHERE (is_latest = true)`
- `idx_post_scores_rule_version`：`CREATE INDEX idx_post_scores_rule_version ON public.post_scores USING btree (rule_version)`
- `post_scores_pkey`：`CREATE UNIQUE INDEX post_scores_pkey ON public.post_scores USING btree (id)`
- `ux_post_scores_latest`：`CREATE UNIQUE INDEX ux_post_scores_latest ON public.post_scores USING btree (post_id) WHERE (is_latest = true)`

## `post_semantic_labels`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('post_semantic_labels_id_seq'::regclass)` |
| `post_id` | `bigint` | NO | `` |
| `l1_category` | `character varying` | YES | `` |
| `l2_business` | `character varying` | YES | `` |
| `l3_scene` | `character varying` | YES | `` |
| `matched_rule_ids` | `ARRAY` | YES | `` |
| `top_terms` | `ARRAY` | YES | `` |
| `raw_scores` | `json` | YES | `` |
| `sentiment_score` | `double precision` | YES | `` |
| `confidence` | `double precision` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |
| `l1_secondary` | `character varying` | YES | `` |
| `tags` | `ARRAY` | YES | `` |

### 约束

- `fk_post_semantic_labels_post` (FOREIGN KEY)：`FOREIGN KEY (post_id) REFERENCES posts_raw(id) ON DELETE RESTRICT`
- `pk_post_semantic_labels` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_post_semantic_labels_post_id` (UNIQUE)：`UNIQUE (post_id)`

### 索引

- `idx_post_semantic_labels_post_id`：`CREATE INDEX idx_post_semantic_labels_post_id ON public.post_semantic_labels USING btree (post_id)`
- `idx_psl_l1`：`CREATE INDEX idx_psl_l1 ON public.post_semantic_labels USING btree (l1_category)`
- `idx_psl_l1_sec`：`CREATE INDEX idx_psl_l1_sec ON public.post_semantic_labels USING btree (l1_secondary)`
- `idx_psl_l2`：`CREATE INDEX idx_psl_l2 ON public.post_semantic_labels USING btree (l2_business)`
- `idx_psl_sentiment`：`CREATE INDEX idx_psl_sentiment ON public.post_semantic_labels USING btree (sentiment_score)`
- `idx_psl_tags`：`CREATE INDEX idx_psl_tags ON public.post_semantic_labels USING gin (tags)`
- `pk_post_semantic_labels`：`CREATE UNIQUE INDEX pk_post_semantic_labels ON public.post_semantic_labels USING btree (id)`
- `uq_post_semantic_labels_post_id`：`CREATE UNIQUE INDEX uq_post_semantic_labels_post_id ON public.post_semantic_labels USING btree (post_id)`

## `posts_archive`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('posts_archive_id_seq'::regclass)` |
| `source` | `character varying` | NO | `'reddit'::character varying` |
| `source_post_id` | `character varying` | NO | `` |
| `version` | `integer` | NO | `1` |
| `archived_at` | `timestamp with time zone` | NO | `now()` |
| `payload` | `jsonb` | NO | `` |

### 约束

- `pk_posts_archive` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_posts_archive_source_post`：`CREATE INDEX idx_posts_archive_source_post ON public.posts_archive USING btree (source, source_post_id)`
- `pk_posts_archive`：`CREATE UNIQUE INDEX pk_posts_archive ON public.posts_archive USING btree (id)`

## `posts_hot`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `source` | `character varying` | NO | `'reddit'::character varying` |
| `source_post_id` | `character varying` | NO | `` |
| `created_at` | `timestamp with time zone` | NO | `` |
| `cached_at` | `timestamp with time zone` | NO | `now()` |
| `expires_at` | `timestamp with time zone` | NO | `(now() + '180 days'::interval)` |
| `title` | `text` | NO | `` |
| `body` | `text` | YES | `` |
| `subreddit` | `character varying` | NO | `` |
| `score` | `integer` | YES | `0` |
| `num_comments` | `integer` | YES | `0` |
| `metadata` | `jsonb` | YES | `` |
| `id` | `bigint` | NO | `nextval('posts_hot_id_seq'::regclass)` |
| `author_id` | `character varying` | YES | `` |
| `author_name` | `character varying` | YES | `` |
| `content_labels` | `jsonb` | YES | `` |
| `entities` | `jsonb` | YES | `` |
| `content_tsvector` | `tsvector` | YES | `` |

### 约束

- `ck_posts_hot_entities_jsonb` (CHECK)：`CHECK (entities IS NULL OR (jsonb_typeof(entities) = ANY (ARRAY['object'::text, 'array'::text]))) NOT VALID`
- `ck_posts_hot_labels_jsonb` (CHECK)：`CHECK (content_labels IS NULL OR (jsonb_typeof(content_labels) = ANY (ARRAY['object'::text, 'array'::text]))) NOT VALID`
- `ck_posts_hot_metadata_jsonb` (CHECK)：`CHECK (metadata IS NULL OR (jsonb_typeof(metadata) = ANY (ARRAY['object'::text, 'array'::text]))) NOT VALID`
- `ck_posts_hot_subreddit_format` (CHECK)：`CHECK (subreddit::text ~ '^r/[a-z0-9_]+$'::text)`
- `posts_hot_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_posts_hot_content_gin`：`CREATE INDEX idx_posts_hot_content_gin ON public.posts_hot USING gin (content_tsvector)`
- `idx_posts_hot_created_at`：`CREATE INDEX idx_posts_hot_created_at ON public.posts_hot USING btree (created_at DESC)`
- `idx_posts_hot_expires_at`：`CREATE INDEX idx_posts_hot_expires_at ON public.posts_hot USING btree (expires_at)`
- `idx_posts_hot_metadata_gin`：`CREATE INDEX idx_posts_hot_metadata_gin ON public.posts_hot USING gin (metadata)`
- `idx_posts_hot_subreddit`：`CREATE INDEX idx_posts_hot_subreddit ON public.posts_hot USING btree (subreddit, created_at DESC)`
- `idx_posts_hot_subreddit_expires`：`CREATE INDEX idx_posts_hot_subreddit_expires ON public.posts_hot USING btree (subreddit, expires_at)`
- `posts_hot_pkey`：`CREATE UNIQUE INDEX posts_hot_pkey ON public.posts_hot USING btree (id)`
- `uq_posts_hot_source_post`：`CREATE UNIQUE INDEX uq_posts_hot_source_post ON public.posts_hot USING btree (source, source_post_id)`

## `posts_quarantine`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('posts_quarantine_id_seq'::regclass)` |
| `source` | `character varying` | NO | `'reddit'::character varying` |
| `source_post_id` | `character varying` | NO | `` |
| `subreddit` | `character varying` | YES | `` |
| `title` | `text` | YES | `` |
| `body` | `text` | YES | `` |
| `author_name` | `character varying` | YES | `` |
| `created_at` | `timestamp with time zone` | YES | `now()` |
| `rejected_at` | `timestamp with time zone` | YES | `now()` |
| `reject_reason` | `text` | YES | `` |
| `original_payload` | `jsonb` | YES | `` |

### 约束

- `posts_quarantine_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `posts_quarantine_pkey`：`CREATE UNIQUE INDEX posts_quarantine_pkey ON public.posts_quarantine USING btree (id)`

## `posts_raw`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('posts_raw_id_seq'::regclass)` |
| `source` | `character varying` | NO | `'reddit'::character varying` |
| `source_post_id` | `character varying` | NO | `` |
| `version` | `integer` | NO | `1` |
| `created_at` | `timestamp with time zone` | NO | `` |
| `fetched_at` | `timestamp with time zone` | NO | `now()` |
| `valid_from` | `timestamp with time zone` | NO | `now()` |
| `valid_to` | `timestamp with time zone` | YES | `'9999-12-31 08:00:00+08'::timestamp with time zone` |
| `is_current` | `boolean` | NO | `true` |
| `author_id` | `character varying` | YES | `` |
| `author_name` | `character varying` | YES | `` |
| `title` | `text` | NO | `` |
| `body` | `text` | YES | `` |
| `body_norm` | `text` | YES | `` |
| `text_norm_hash` | `character varying` | YES | `` |
| `url` | `text` | YES | `` |
| `subreddit` | `character varying` | NO | `` |
| `score` | `integer` | YES | `0` |
| `num_comments` | `integer` | YES | `0` |
| `is_deleted` | `boolean` | YES | `false` |
| `edit_count` | `integer` | YES | `0` |
| `lang` | `character varying` | YES | `` |
| `metadata` | `jsonb` | YES | `` |
| `is_duplicate` | `boolean` | NO | `false` |
| `duplicate_of_id` | `bigint` | YES | `` |
| `spam_category` | `character varying` | YES | `` |
| `value_score` | `smallint` | YES | `` |
| `business_pool` | `character varying` | YES | `` |
| `community_id` | `integer` | YES | `` |
| `score_source` | `character varying` | YES | `` |
| `score_version` | `integer` | YES | `1` |
| `first_seen_at` | `timestamp with time zone` | YES | `now()` |
| `source_track` | `character varying` | YES | `'incremental'::character varying` |
| `crawl_run_id` | `uuid` | YES | `` |
| `community_run_id` | `uuid` | YES | `` |

### 约束

- `ck_posts_raw_business_pool` (CHECK)：`CHECK (business_pool::text = ANY (ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying]::text[]))`
- `ck_posts_raw_metadata_jsonb` (CHECK)：`CHECK (metadata IS NULL OR (jsonb_typeof(metadata) = ANY (ARRAY['object'::text, 'array'::text]))) NOT VALID`
- `ck_posts_raw_subreddit_format` (CHECK)：`CHECK (subreddit::text ~ '^r/[a-z0-9_]+$'::text)`
- `ck_posts_raw_valid_period` (CHECK)：`CHECK (valid_from < valid_to OR valid_to = '9999-12-31 00:00:00'::timestamp without time zone)`
- `ck_posts_raw_version_positive` (CHECK)：`CHECK (version > 0)`
- `fk_posts_raw_author` (FOREIGN KEY)：`FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE SET NULL`
- `fk_posts_raw_duplicate_of` (FOREIGN KEY)：`FOREIGN KEY (duplicate_of_id) REFERENCES posts_raw(id) ON DELETE RESTRICT`
- `pk_posts_raw` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_posts_raw_source_version` (UNIQUE)：`UNIQUE (source, source_post_id, version)`

### 索引

- `idx_posts_fulltext`：`CREATE INDEX idx_posts_fulltext ON public.posts_raw USING gin (to_tsvector('english'::regconfig, ((COALESCE(title, ''::text) || ' '::text) || COALESCE(body, ''::text))))`
- `idx_posts_raw_business_pool`：`CREATE INDEX idx_posts_raw_business_pool ON public.posts_raw USING btree (business_pool)`
- `idx_posts_raw_community_id`：`CREATE INDEX idx_posts_raw_community_id ON public.posts_raw USING btree (community_id)`
- `idx_posts_raw_community_run_id`：`CREATE INDEX idx_posts_raw_community_run_id ON public.posts_raw USING btree (community_run_id) WHERE (community_run_id IS NOT NULL)`
- `idx_posts_raw_crawl_run_id`：`CREATE INDEX idx_posts_raw_crawl_run_id ON public.posts_raw USING btree (crawl_run_id) WHERE (crawl_run_id IS NOT NULL)`
- `idx_posts_raw_created_at`：`CREATE INDEX idx_posts_raw_created_at ON public.posts_raw USING btree (created_at DESC)`
- `idx_posts_raw_current`：`CREATE INDEX idx_posts_raw_current ON public.posts_raw USING btree (source, source_post_id, is_current) WHERE (is_current = true)`
- `idx_posts_raw_duplicate_flag`：`CREATE INDEX idx_posts_raw_duplicate_flag ON public.posts_raw USING btree (is_duplicate)`
- `idx_posts_raw_duplicate_of`：`CREATE INDEX idx_posts_raw_duplicate_of ON public.posts_raw USING btree (duplicate_of_id)`
- `idx_posts_raw_fetched_at`：`CREATE INDEX idx_posts_raw_fetched_at ON public.posts_raw USING btree (fetched_at DESC)`
- `idx_posts_raw_source_post_id`：`CREATE INDEX idx_posts_raw_source_post_id ON public.posts_raw USING btree (source, source_post_id)`
- `idx_posts_raw_source_track`：`CREATE INDEX idx_posts_raw_source_track ON public.posts_raw USING btree (source_track)`
- `idx_posts_raw_spam_category`：`CREATE INDEX idx_posts_raw_spam_category ON public.posts_raw USING btree (spam_category)`
- `idx_posts_raw_subreddit`：`CREATE INDEX idx_posts_raw_subreddit ON public.posts_raw USING btree (subreddit, created_at DESC)`
- `idx_posts_raw_text_hash`：`CREATE INDEX idx_posts_raw_text_hash ON public.posts_raw USING btree (text_norm_hash)`
- `idx_posts_raw_value_score`：`CREATE INDEX idx_posts_raw_value_score ON public.posts_raw USING btree (value_score DESC)`
- `pk_posts_raw`：`CREATE UNIQUE INDEX pk_posts_raw ON public.posts_raw USING btree (id)`
- `uq_posts_raw_source_version`：`CREATE UNIQUE INDEX uq_posts_raw_source_version ON public.posts_raw USING btree (source, source_post_id, version)`

## `quality_metrics`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('quality_metrics_id_seq'::regclass)` |
| `date` | `date` | NO | `` |
| `collection_success_rate` | `numeric` | NO | `` |
| `deduplication_rate` | `numeric` | NO | `` |
| `processing_time_p50` | `numeric` | NO | `` |
| `processing_time_p95` | `numeric` | NO | `` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |

### 约束

- `ck_quality_metrics_collection_rate_range` (CHECK)：`CHECK (collection_success_rate >= 0.00 AND collection_success_rate <= 1.00)`
- `ck_quality_metrics_dedup_rate_range` (CHECK)：`CHECK (deduplication_rate >= 0.00 AND deduplication_rate <= 1.00)`
- `ck_quality_metrics_p50_positive` (CHECK)：`CHECK (processing_time_p50 >= 0::numeric)`
- `ck_quality_metrics_p95_gte_p50` (CHECK)：`CHECK (processing_time_p95 >= processing_time_p50)`
- `ck_quality_metrics_p95_positive` (CHECK)：`CHECK (processing_time_p95 >= 0::numeric)`
- `pk_quality_metrics` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_quality_metrics_date`：`CREATE UNIQUE INDEX idx_quality_metrics_date ON public.quality_metrics USING btree (date)`
- `pk_quality_metrics`：`CREATE UNIQUE INDEX pk_quality_metrics ON public.quality_metrics USING btree (id)`

## `reports`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `analysis_id` | `uuid` | NO | `` |
| `html_content` | `text` | NO | `` |
| `status` | `character varying` | NO | `'active'::character varying` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `template_version` | `character varying` | NO | `'1.0'::character varying` |
| `generated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |

### 约束

- `ck_reports_html_size` (CHECK)：`CHECK (length(html_content) <= 10485760)`
- `ck_reports_status` (CHECK)：`CHECK (status::text = ANY (ARRAY['active'::character varying::text, 'deprecated'::character varying::text, 'draft'::character varying::text]))`
- `reports_analysis_id_fkey` (FOREIGN KEY)：`FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE`
- `reports_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_reports_template`：`CREATE INDEX idx_reports_template ON public.reports USING btree (template_version)`
- `ix_reports_analysis_active`：`CREATE INDEX ix_reports_analysis_active ON public.reports USING btree (analysis_id) WHERE ((status)::text = 'active'::text)`
- `ix_reports_created_desc`：`CREATE INDEX ix_reports_created_desc ON public.reports USING btree (created_at DESC)`
- `reports_pkey`：`CREATE UNIQUE INDEX reports_pkey ON public.reports USING btree (id)`

## `semantic_audit_logs`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('semantic_audit_logs_id_seq'::regclass)` |
| `action` | `character varying` | NO | `` |
| `entity_type` | `character varying` | NO | `` |
| `entity_id` | `bigint` | NO | `` |
| `changes` | `jsonb` | YES | `` |
| `operator_id` | `uuid` | YES | `` |
| `operator_ip` | `character varying` | YES | `` |
| `reason` | `text` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |

### 约束

- `fk_semantic_audit_logs_operator_id_users` (FOREIGN KEY)：`FOREIGN KEY (operator_id) REFERENCES users(id) ON DELETE SET NULL`
- `pk_semantic_audit_logs` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_semantic_audit_logs_changes_gin`：`CREATE INDEX idx_semantic_audit_logs_changes_gin ON public.semantic_audit_logs USING gin (changes)`
- `ix_semantic_audit_logs_created_at`：`CREATE INDEX ix_semantic_audit_logs_created_at ON public.semantic_audit_logs USING btree (created_at)`
- `ix_semantic_audit_logs_entity`：`CREATE INDEX ix_semantic_audit_logs_entity ON public.semantic_audit_logs USING btree (entity_type, entity_id)`
- `ix_semantic_audit_logs_operator_id`：`CREATE INDEX ix_semantic_audit_logs_operator_id ON public.semantic_audit_logs USING btree (operator_id)`
- `pk_semantic_audit_logs`：`CREATE UNIQUE INDEX pk_semantic_audit_logs ON public.semantic_audit_logs USING btree (id)`

## `semantic_candidates`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('semantic_candidates_id_seq'::regclass)` |
| `term` | `character varying` | NO | `` |
| `frequency` | `integer` | NO | `` |
| `source` | `character varying` | NO | `` |
| `first_seen_at` | `timestamp with time zone` | NO | `` |
| `last_seen_at` | `timestamp with time zone` | NO | `` |
| `status` | `character varying` | NO | `` |
| `reviewed_by` | `uuid` | YES | `` |
| `reviewed_at` | `timestamp with time zone` | YES | `` |
| `reject_reason` | `text` | YES | `` |
| `approved_category` | `character varying` | YES | `` |
| `approved_layer` | `character varying` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |
| `created_by` | `uuid` | YES | `` |
| `updated_by` | `uuid` | YES | `` |

### 约束

- `ck_semantic_candidates_ck_semantic_candidates_status_valid` (CHECK)：`CHECK (status::text = ANY (ARRAY['pending'::character varying::text, 'approved'::character varying::text, 'rejected'::character varying::text]))`
- `fk_semantic_candidates_created_by_users` (FOREIGN KEY)：`FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_semantic_candidates_reviewed_by_users` (FOREIGN KEY)：`FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL`
- `fk_semantic_candidates_updated_by_users` (FOREIGN KEY)：`FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- `pk_semantic_candidates` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_semantic_candidates_term` (UNIQUE)：`UNIQUE (term)`

### 索引

- `ix_semantic_candidates_first_seen_at`：`CREATE INDEX ix_semantic_candidates_first_seen_at ON public.semantic_candidates USING btree (first_seen_at)`
- `ix_semantic_candidates_frequency`：`CREATE INDEX ix_semantic_candidates_frequency ON public.semantic_candidates USING btree (frequency)`
- `ix_semantic_candidates_status`：`CREATE INDEX ix_semantic_candidates_status ON public.semantic_candidates USING btree (status)`
- `pk_semantic_candidates`：`CREATE UNIQUE INDEX pk_semantic_candidates ON public.semantic_candidates USING btree (id)`
- `uq_semantic_candidates_term`：`CREATE UNIQUE INDEX uq_semantic_candidates_term ON public.semantic_candidates USING btree (term)`

## `semantic_concepts`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('semantic_concepts_id_seq'::regclass)` |
| `code` | `character varying` | NO | `` |
| `name` | `character varying` | NO | `` |
| `description` | `text` | YES | `` |
| `domain` | `character varying` | NO | `'general'::character varying` |
| `is_active` | `boolean` | NO | `true` |
| `created_at` | `timestamp with time zone` | YES | `now()` |
| `updated_at` | `timestamp with time zone` | YES | `now()` |

### 约束

- `pk_semantic_concepts` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_semantic_concepts_code` (UNIQUE)：`UNIQUE (code)`

### 索引

- `pk_semantic_concepts`：`CREATE UNIQUE INDEX pk_semantic_concepts ON public.semantic_concepts USING btree (id)`
- `uq_semantic_concepts_code`：`CREATE UNIQUE INDEX uq_semantic_concepts_code ON public.semantic_concepts USING btree (code)`

## `semantic_rules`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('semantic_rules_id_seq'::regclass)` |
| `concept_id` | `integer` | NO | `` |
| `term` | `character varying` | NO | `` |
| `rule_type` | `character varying` | NO | `'keyword'::character varying` |
| `weight` | `numeric` | NO | `1.0` |
| `is_active` | `boolean` | NO | `true` |
| `hit_count` | `integer` | NO | `0` |
| `last_hit_at` | `timestamp with time zone` | YES | `` |
| `meta` | `json` | NO | `'{}'::jsonb` |
| `created_at` | `timestamp with time zone` | YES | `now()` |
| `updated_at` | `timestamp with time zone` | YES | `now()` |
| `domain` | `character varying` | YES | `` |
| `aspect` | `character varying` | YES | `` |
| `source` | `character varying` | YES | `'yaml'::character varying` |

### 约束

- `fk_semantic_rules_concept_id_semantic_concepts` (FOREIGN KEY)：`FOREIGN KEY (concept_id) REFERENCES semantic_concepts(id) ON DELETE CASCADE`
- `pk_semantic_rules` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_semantic_rules_term_type` (UNIQUE)：`UNIQUE (concept_id, term, rule_type)`

### 索引

- `idx_semantic_rules_active_concept`：`CREATE INDEX idx_semantic_rules_active_concept ON public.semantic_rules USING btree (concept_id) WHERE (is_active = true)`
- `idx_semantic_rules_concept`：`CREATE INDEX idx_semantic_rules_concept ON public.semantic_rules USING btree (concept_id)`
- `idx_semantic_rules_term`：`CREATE INDEX idx_semantic_rules_term ON public.semantic_rules USING btree (term)`
- `ix_semantic_rules_domain`：`CREATE INDEX ix_semantic_rules_domain ON public.semantic_rules USING btree (domain)`
- `pk_semantic_rules`：`CREATE UNIQUE INDEX pk_semantic_rules ON public.semantic_rules USING btree (id)`
- `uq_semantic_rules_term_type`：`CREATE UNIQUE INDEX uq_semantic_rules_term_type ON public.semantic_rules USING btree (concept_id, term, rule_type)`

## `semantic_terms`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('semantic_terms_id_seq'::regclass)` |
| `canonical` | `character varying` | NO | `` |
| `aliases` | `ARRAY` | YES | `` |
| `category` | `character varying` | NO | `` |
| `layer` | `character varying` | YES | `` |
| `precision_tag` | `character varying` | YES | `` |
| `weight` | `numeric` | YES | `` |
| `polarity` | `character varying` | YES | `` |
| `lifecycle` | `character varying` | NO | `` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |

### 约束

- `pk_semantic_terms` (PRIMARY KEY)：`PRIMARY KEY (id)`
- `uq_semantic_terms_canonical` (UNIQUE)：`UNIQUE (canonical)`

### 索引

- `ix_semantic_terms_canonical`：`CREATE UNIQUE INDEX ix_semantic_terms_canonical ON public.semantic_terms USING btree (canonical)`
- `ix_semantic_terms_category_layer`：`CREATE INDEX ix_semantic_terms_category_layer ON public.semantic_terms USING btree (category, layer)`
- `ix_semantic_terms_lifecycle`：`CREATE INDEX ix_semantic_terms_lifecycle ON public.semantic_terms USING btree (lifecycle)`
- `pk_semantic_terms`：`CREATE UNIQUE INDEX pk_semantic_terms ON public.semantic_terms USING btree (id)`
- `uq_semantic_terms_canonical`：`CREATE UNIQUE INDEX uq_semantic_terms_canonical ON public.semantic_terms USING btree (canonical)`

## `storage_metrics`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('storage_metrics_id_seq'::regclass)` |
| `collected_at` | `timestamp with time zone` | NO | `now()` |
| `posts_raw_total` | `bigint` | NO | `'0'::bigint` |
| `posts_raw_current` | `bigint` | NO | `'0'::bigint` |
| `posts_hot_total` | `bigint` | NO | `'0'::bigint` |
| `posts_hot_expired` | `bigint` | NO | `'0'::bigint` |
| `unique_subreddits` | `bigint` | NO | `'0'::bigint` |
| `total_versions` | `bigint` | NO | `'0'::bigint` |
| `dedup_rate` | `numeric` | NO | `'0'::numeric` |
| `notes` | `jsonb` | YES | `` |

### 约束

- `pk_storage_metrics` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_storage_metrics_collected_at`：`CREATE INDEX idx_storage_metrics_collected_at ON public.storage_metrics USING btree (collected_at)`
- `pk_storage_metrics`：`CREATE UNIQUE INDEX pk_storage_metrics ON public.storage_metrics USING btree (id)`

## `subreddit_snapshots`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `bigint` | NO | `nextval('subreddit_snapshots_id_seq'::regclass)` |
| `subreddit` | `character varying` | NO | `` |
| `captured_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `subscribers` | `character varying` | YES | `` |
| `active_user_count` | `character varying` | YES | `` |
| `rules_text` | `text` | YES | `` |
| `over18` | `boolean` | YES | `` |
| `moderation_score` | `integer` | YES | `` |

### 约束

- `pk_subreddit_snapshots` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_subreddit_snapshots_subreddit`：`CREATE INDEX idx_subreddit_snapshots_subreddit ON public.subreddit_snapshots USING btree (subreddit)`
- `idx_subreddit_snapshots_time`：`CREATE INDEX idx_subreddit_snapshots_time ON public.subreddit_snapshots USING btree (subreddit, captured_at)`
- `pk_subreddit_snapshots`：`CREATE UNIQUE INDEX pk_subreddit_snapshots ON public.subreddit_snapshots USING btree (id)`

## `tasks`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `user_id` | `uuid` | NO | `` |
| `product_description` | `text` | NO | `` |
| `status` | `character varying` | NO | `'pending'::character varying` |
| `error_message` | `text` | YES | `` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `completed_at` | `timestamp with time zone` | YES | `` |
| `started_at` | `timestamp with time zone` | YES | `` |
| `retry_count` | `integer` | NO | `0` |
| `failure_category` | `character varying` | YES | `` |
| `last_retry_at` | `timestamp with time zone` | YES | `` |
| `dead_letter_at` | `timestamp with time zone` | YES | `` |
| `mode` | `character varying` | NO | `'market_insight'::character varying` |
| `topic_profile_id` | `character varying` | YES | `` |
| `audit_level` | `character varying` | NO | `'lab'::character varying` |

### 约束

- `ck_tasks_ck_tasks_valid_audit_level` (CHECK)：`CHECK (audit_level::text = ANY (ARRAY['gold'::character varying, 'lab'::character varying, 'noise'::character varying]::text[]))`
- `ck_tasks_ck_tasks_valid_mode` (CHECK)：`CHECK (mode::text = ANY (ARRAY['market_insight'::character varying, 'operations'::character varying]::text[]))`
- `ck_tasks_ck_tasks_valid_topic_profile_id` (CHECK)：`CHECK (topic_profile_id IS NULL OR topic_profile_id::text <> ''::text)`
- `ck_tasks_completed_status_alignment` (CHECK)：`CHECK (status::text = 'completed'::text AND completed_at IS NOT NULL OR status::text <> 'completed'::text AND completed_at IS NULL)`
- `ck_tasks_completion_consistency` (CHECK)：`CHECK (status::text = 'completed'::text AND completed_at IS NOT NULL OR status::text <> 'completed'::text AND completed_at IS NULL)`
- `ck_tasks_description_length` (CHECK)：`CHECK (char_length(product_description) >= 10 AND char_length(product_description) <= 2000)`
- `ck_tasks_error_length` (CHECK)：`CHECK (error_message IS NULL OR char_length(error_message) <= 1000)`
- `ck_tasks_error_message_when_failed` (CHECK)：`CHECK (status::text = 'failed'::text AND error_message IS NOT NULL OR status::text <> 'failed'::text AND (error_message IS NULL OR error_message = ''::text))`
- `ck_tasks_error_msg_failed` (CHECK)：`CHECK (status::text = 'failed'::text AND error_message IS NOT NULL OR status::text <> 'failed'::text AND (error_message IS NULL OR error_message = ''::text))`
- `ck_tasks_valid_completion_time` (CHECK)：`CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)`
- `tasks_user_id_fkey` (FOREIGN KEY)：`FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- `tasks_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_tasks_completed_cleanup`：`CREATE INDEX idx_tasks_completed_cleanup ON public.tasks USING btree (status, completed_at) WHERE (((status)::text = 'completed'::text) AND (completed_at IS NOT NULL))`
- `idx_tasks_failed_cleanup`：`CREATE INDEX idx_tasks_failed_cleanup ON public.tasks USING btree (status, updated_at) WHERE (((status)::text = 'failed'::text) AND (updated_at IS NOT NULL))`
- `ix_tasks_audit_level`：`CREATE INDEX ix_tasks_audit_level ON public.tasks USING btree (audit_level)`
- `ix_tasks_processing`：`CREATE INDEX ix_tasks_processing ON public.tasks USING btree (status, created_at) WHERE ((status)::text = 'processing'::text)`
- `ix_tasks_status`：`CREATE INDEX ix_tasks_status ON public.tasks USING btree (status) WHERE ((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('processing'::character varying)::text]))`
- `ix_tasks_status_created`：`CREATE INDEX ix_tasks_status_created ON public.tasks USING btree (status, created_at DESC)`
- `ix_tasks_topic_profile_id`：`CREATE INDEX ix_tasks_topic_profile_id ON public.tasks USING btree (topic_profile_id)`
- `ix_tasks_user_created`：`CREATE INDEX ix_tasks_user_created ON public.tasks USING btree (user_id, created_at DESC)`
- `ix_tasks_user_status`：`CREATE INDEX ix_tasks_user_status ON public.tasks USING btree (user_id, status)`
- `tasks_pkey`：`CREATE UNIQUE INDEX tasks_pkey ON public.tasks USING btree (id)`

## `tier_audit_logs`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('tier_audit_logs_id_seq'::regclass)` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |
| `community_name` | `character varying` | NO | `` |
| `action` | `character varying` | NO | `` |
| `field_changed` | `character varying` | NO | `` |
| `from_value` | `character varying` | YES | `` |
| `to_value` | `character varying` | NO | `` |
| `changed_by` | `character varying` | NO | `` |
| `change_source` | `character varying` | NO | `'manual'::character varying` |
| `reason` | `text` | YES | `` |
| `snapshot_before` | `jsonb` | NO | `` |
| `snapshot_after` | `jsonb` | NO | `` |
| `suggestion_id` | `integer` | YES | `` |
| `is_rolled_back` | `boolean` | NO | `false` |
| `rolled_back_at` | `timestamp with time zone` | YES | `` |
| `rolled_back_by` | `character varying` | YES | `` |

### 约束

- `pk_tier_audit_logs` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `ix_tier_audit_logs_action`：`CREATE INDEX ix_tier_audit_logs_action ON public.tier_audit_logs USING btree (action)`
- `ix_tier_audit_logs_community_name`：`CREATE INDEX ix_tier_audit_logs_community_name ON public.tier_audit_logs USING btree (community_name)`
- `ix_tier_audit_logs_is_rolled_back`：`CREATE INDEX ix_tier_audit_logs_is_rolled_back ON public.tier_audit_logs USING btree (is_rolled_back)`
- `pk_tier_audit_logs`：`CREATE UNIQUE INDEX pk_tier_audit_logs ON public.tier_audit_logs USING btree (id)`

## `tier_suggestions`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `integer` | NO | `nextval('tier_suggestions_id_seq'::regclass)` |
| `created_at` | `timestamp with time zone` | NO | `now()` |
| `updated_at` | `timestamp with time zone` | NO | `now()` |
| `community_name` | `character varying` | NO | `` |
| `current_tier` | `character varying` | NO | `` |
| `suggested_tier` | `character varying` | NO | `` |
| `confidence` | `double precision` | NO | `` |
| `reasons` | `jsonb` | NO | `` |
| `metrics` | `jsonb` | NO | `` |
| `status` | `character varying` | NO | `'pending'::character varying` |
| `generated_at` | `timestamp with time zone` | NO | `now()` |
| `reviewed_by` | `character varying` | YES | `` |
| `reviewed_at` | `timestamp with time zone` | YES | `` |
| `applied_at` | `timestamp with time zone` | YES | `` |
| `priority_score` | `integer` | NO | `0` |
| `expires_at` | `timestamp with time zone` | NO | `` |

### 约束

- `pk_tier_suggestions` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `ix_tier_suggestions_community_name`：`CREATE INDEX ix_tier_suggestions_community_name ON public.tier_suggestions USING btree (community_name)`
- `ix_tier_suggestions_status`：`CREATE INDEX ix_tier_suggestions_status ON public.tier_suggestions USING btree (status)`
- `pk_tier_suggestions`：`CREATE UNIQUE INDEX pk_tier_suggestions ON public.tier_suggestions USING btree (id)`

## `users`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `id` | `uuid` | NO | `gen_random_uuid()` |
| `tenant_id` | `uuid` | NO | `gen_random_uuid()` |
| `email` | `character varying` | NO | `` |
| `password_hash` | `character varying` | NO | `` |
| `email_verified` | `boolean` | NO | `false` |
| `is_active` | `boolean` | NO | `true` |
| `created_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp with time zone` | NO | `CURRENT_TIMESTAMP` |
| `membership_level` | `USER-DEFINED` | NO | `` |

### 约束

- `ck_users_email_format` (CHECK)：`CHECK (email::text ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::text)`
- `ck_users_membership_level` (CHECK)：`CHECK (membership_level = ANY (ARRAY['free'::membership_level, 'pro'::membership_level, 'enterprise'::membership_level]))`
- `ck_users_password_hash_format` (CHECK)：`CHECK (password_hash::text ~ '^pbkdf2_sha256\$'::text OR password_hash::text ~ '^\$2[aby]?\$\d{2}\$'::text)`
- `users_pkey` (PRIMARY KEY)：`PRIMARY KEY (id)`

### 索引

- `idx_users_active_login`：`CREATE INDEX idx_users_active_login ON public.users USING btree (is_active, created_at) WHERE (is_active = true)`
- `ix_users_email_lookup`：`CREATE INDEX ix_users_email_lookup ON public.users USING btree (email) WHERE (is_active = true)`
- `ix_users_tenant_active`：`CREATE INDEX ix_users_tenant_active ON public.users USING btree (tenant_id, is_active) WHERE (is_active = true)`
- `ix_users_tenant_email_unique`：`CREATE UNIQUE INDEX ix_users_tenant_email_unique ON public.users USING btree (tenant_id, email) WHERE (is_active = true)`
- `ix_users_tenant_id`：`CREATE INDEX ix_users_tenant_id ON public.users USING btree (tenant_id)`
- `users_pkey`：`CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id)`

## `vertical_map`

### 字段

| 字段 | 类型 | 可空 | 默认值 |
|---|---|---:|---|
| `subreddit` | `character varying` | NO | `` |
| `vertical` | `character varying` | YES | `` |

### 约束

- `vertical_map_pkey` (PRIMARY KEY)：`PRIMARY KEY (subreddit)`

### 索引

- `vertical_map_pkey`：`CREATE UNIQUE INDEX vertical_map_pkey ON public.vertical_map USING btree (subreddit)`
