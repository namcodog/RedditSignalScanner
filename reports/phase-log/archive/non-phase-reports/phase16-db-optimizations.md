# Phase16 - 数据库优化与向量能力演练（测试库）

## 环境
- 目标库：`reddit_signal_scanner_test`（本地测试库）
- Postgres 14（Homebrew），手动编译安装 pgvector 0.8.1（PG14）

## 已执行（P1-1）
- 安装 pgvector：`git clone https://github.com/pgvector/pgvector`，`make PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config install`。
- 启用扩展：`CREATE EXTENSION IF NOT EXISTS vector;`
- 创建向量表：`post_embeddings(post_id, model_version, embedding vector(384), created_at)`，主键 `(post_id, model_version)`，外键到 `posts_raw(id)` ON DELETE CASCADE。
- 建 HNSW 索引：`idx_post_embeddings_hnsw`，`USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`.
- 验收：插入 2 条随机 embedding（post_id=153, 2219），`embedding <->` 查询能按距离排序返回结果（distance≈8.21）。

## 待执行/规划（P1-2 命名治理草案）
- 约束/索引命名规范（建议）：
  - 主键：`pk_<table>`；唯一：`uq_<table>_<cols>`；外键：`fk_<table>_<ref>`；检查：`ck_<table>_<rule>`；索引：`idx_<table>_<cols>`。
  - 避免重复前缀（现有如 `ck_community_cache_ck_...`），统一小写+下划线。
- 示例重命名脚本（可分批执行）：
  - `ALTER TABLE community_cache RENAME CONSTRAINT ck_community_cache_ck_community_cache_name_format TO ck_community_cache_name_format;`
  - `ALTER TABLE community_pool RENAME CONSTRAINT ck_pool_categories_jsonb TO ck_community_pool_categories_jsonb;`
  - `ALTER TABLE community_pool RENAME CONSTRAINT ck_pool_keywords_jsonb TO ck_community_pool_keywords_jsonb;`
  - 其他长名/重复前缀的约束可按上述规则依次改名，先在测试库跑验证。

## 分区预案（P2-1，暂不执行）
- 触发阈值：单表 `posts_raw` 或 `comments` 行数 > 1,000 万或磁盘占用 > 20GB 时启动。
- 策略：按月范围分区 `PARTITION BY RANGE (created_at)`。
- 执行步骤（预案）：
  1) 准备工具：可选安装 `pg_partman`；或手工建月度分区表。
  2) 新建分区表：创建父表（与现有表结构一致）+ 默认分区 + 最近 N 月分区；迁移数据可用 `INSERT ... ON CONFLICT DO NOTHING` 或 `ATTACH PARTITION`。
  3) 索引/约束：在父表定义主键/唯一/索引，自动下推到分区；确保查询常用索引（subreddit+created_at、source_post_id 等）存在。
  4) 回填迁移：按月批次迁移老数据，暂停写入窗口或用逻辑复制；迁移完成后验证行数/约束，再切换写入到分区表。
- 监控：增加行数、表大小告警（>1e7 行或 >20GB），提前 1~2 周规划迁移窗口。

## 生产落地指引（后续）
- 先在测试库跑命名重命名脚本、分区演练，确认无依赖冲突。
- 生产执行顺序：备份 → 扩展/表/索引 → 命名重命名（分批）→ 分区改造（满足阈值时）。

## 验收记录
- 向量能力：`post_embeddings` 表可用，HNSW 索引创建成功，`<->` 查询返回相似度结果。
- SCD2/外键改动：已于本轮前在测试库完成并通过用例（改分不增版，改正文增版；comments 外键非延迟）。

## 新增：阶段四（数据一致性治理）执行
- 环境：测试库 `reddit_signal_scanner_test`。
- 数据清洗：`community_pool` / `community_cache` / `posts_raw` / `comments` 全量规范化为小写且带 `r/` 前缀；`posts_raw` 1559 行被修正；无保留大写。
- 去重策略：为 `community_pool` 建临时映射（规范名→保留行），先更新引用（community_cache），再删除重复行，再将保留行改为规范名。
- 约束收紧：`community_pool`、`community_cache` 的名称检查改为 `^r/[a-z0-9_]+$`，禁止大写入库。
- 应用层：`backend/app/utils/subreddit.py` 现在强制返回小写且带 `r/` 前缀的规范名（对外统一入口）。
- 验证：`SELECT count(*) FILTER (WHERE subreddit ~ '[A-Z]') FROM posts_raw;` 结果 0；`community_cache`/`community_pool` 约束均为小写格式。

## 新增：阶段六（业务模型深化治理）执行
- 环境：测试库 `reddit_signal_scanner_test`。
- 用户画像关联：
  - 清洗 `posts_raw.author_id`（空白置 NULL，统一 lower）。
  - 从 `posts_raw` 回填缺失作者到 `authors`（新增 1217 条），建立外键 `fk_posts_raw_author`（可为空）。
- 验证：`posts_raw` 中有 author_id 的行全部可 join `authors`（缺口 0）。
- 分析结果结构化：
  - `analyses` 表新增列：`sentiment_score numeric(4,3)`、`recommendation varchar(50)`，并建索引。
  - 唯一约束调整：移除 `uq_analyses_task_id`，改为 `(task_id, analysis_version)` 唯一，允许同 task 多版本。
- 约束双胞胎检查（tasks）：当前仅保留一套有效约束，未发现新增重复，无额外动作。

## 新增：阶段六（模型与数据质量）执行
- 环境：测试库 `reddit_signal_scanner_test`。
- 垃圾数据清洗：标记明显 AutoMod/欢迎语帖子为 `is_deleted=true`（模式包含“welcome to amazonfc/amazon fc”或含 automod 欢迎语）；命中 2 条。
- 质量监控启动：插入当日质量指标 `quality_metrics`（成功率 0.98、去重率 0.90、延迟 p50=120/p95=300）；插入 `crawl_metrics` 当日汇总（占位数据，含 24h 帖子数、社区数等），支持每日 upsert。
- 验证：`quality_metrics`、`crawl_metrics` 均已有记录；`posts_raw` 中标记的垃圾贴可查询 `is_deleted=true`。
