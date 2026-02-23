# Phase 124 - 2025-12-22 备份“全量复原”：修复 posts_latest 卡死 + 切回真实社区池（166盘回归）

日期：2026-01-20

## 目标（说人话）
把本地的“正式库”从 **1/03 之后那套被清空/跑偏的状态**拉回到 **12-22 备份那套真实数据**：
- 社区池回到 166 个确认盘（并保留 paused/blacklisted 的状态语义）
- 抓取数据（posts/comments）回到备份时的真实量级
- 新系统（到 20260103_000003）能在这套数据上稳定跑
- 不再让旧的 queued/running 作业单自动继续跑，避免恢复后又污染

## 发生了什么（现象）
在原 `reddit_signal_scanner` 库里：
- 社区池规模异常（只剩几十个“垃圾盘”的感觉），数据量也明显偏小
- `post_embeddings/comment_scores` 为空或缺失，整体像是“被清空后重新抓了一点点”

用户诉求是：**用 2025-12-22 的备份做底座，全恢复，并且不要再混乱/污染。**

## 根因（已精确定位）
### 1) 直接 pg_restore 会卡死：posts_latest 物化视图刷新失败
对 `backups/prod_backup_final_confirm_20251222.dump` 做全量 restore 时，失败点在：
- `REFRESH MATERIALIZED VIEW public.posts_latest`
- 报错：`idx_posts_latest_unique` 需要 `(source, source_post_id)` 唯一，但备份数据里出现重复 current

### 2) 备份数据里存在 SCD2 不一致：同一帖子多条 is_current=true
`posts_latest` 的定义是：
- `FROM posts_raw WHERE is_current=true`
且有 `UNIQUE (source, source_post_id)`。

但备份里存在：
- 同一个 `(source, source_post_id)`，有两条（甚至多条）`is_current=true`（通常是 version=1 和 version=2 都被标成 current）。

### 3) 不能直接 UPDATE is_current：enforce_scd2_posts_raw 触发器会“把你改回去”
`posts_raw` 上的 `enforce_scd2_posts_raw` 触发器规则是：
- 不改 title/body 时，UPDATE 会被强行“原地更新”，把 `is_current/valid_to` 还原成 OLD 值
所以修复重复 current 必须 **临时禁用该触发器** 才能落地。

## 精确修复（可复现步骤）
### A) 先让 restore 跑完：跳过 posts_latest 的 “MATERIALIZED VIEW DATA”
1) 重建临时恢复库：
- `reddit_signal_scanner_restored_20251222`
- `CREATE EXTENSION vector;`

2) 生成 TOC list 并注释掉：
- `MATERIALIZED VIEW DATA public posts_latest`
文件：`backups/restore_20251222_no_posts_latest_data.list`

3) 用 list 恢复（避免 restore 阶段触发 MV refresh）：
- `pg_restore --no-owner --no-privileges -L backups/restore_20251222_no_posts_latest_data.list ...`

### B) 修复 posts_raw 重复 current（只修重复项，不动正常数据）
在恢复库内：
1) 检查重复 current keys 数量：
- `dup_current_keys = 500`

2) 事务内临时禁用触发器 + 修复：
- `ALTER TABLE posts_raw DISABLE TRIGGER enforce_scd2_posts_raw;`
- 对每个 `(source, source_post_id)`：
  - 保留 `version` 最大的那条为 current
  - 其他 current 版本统一设为 `is_current=false`
  - 并把旧版本 `valid_to` 修到不小于 `valid_from + 1s`（避免违反 valid period 约束）
- `ALTER TABLE posts_raw ENABLE TRIGGER enforce_scd2_posts_raw;`

3) 修复后验收：
- `dup_current_keys = 0`

### C) 手动刷新 posts_latest（此时不会再撞唯一约束）
- `REFRESH MATERIALIZED VIEW posts_latest;`

### D) 把恢复库迁移到最新 schema（对齐新系统）
对恢复库执行：
- `alembic upgrade head`
最终版本：
- `alembic_version = 20260103_000003`

### E) 封口清理（避免恢复后“旧单续跑/口径打架/黑名单进主表”）
1) 口径对齐（paused 真暂停）：
- `community_pool.status='paused' -> is_active=false`
- 同步 `community_cache.is_active=false`

2) 防止恢复后自动继续跑旧作业单：
- `crawler_run_targets`：`queued/running -> failed`
- `error_code='restore_reset'`

3) 黑名单社区内容不进主表/热缓存（避免主链路跑偏）：
- `posts_raw` 删除黑名单社区数据（本库仅 38 条）
- `posts_hot` 删除黑名单社区数据（本库 100 条）
- 刷新 `posts_latest`

### F) 本地“正式库”切回恢复库（避免你继续查到那套脏库）
1) 旧库改名保留（留作备份/对照）：
- `reddit_signal_scanner` -> `reddit_signal_scanner_corrupted_20260120_201546`

2) 恢复库改名成为正式库：
- `reddit_signal_scanner_restored_20251222` -> `reddit_signal_scanner`

3) 补齐角色权限（因为 restore 用了 `--no-privileges`）：
- 给 `app_user/rss_app`：
  - `GRANT CONNECT ON DATABASE reddit_signal_scanner`
  - `GRANT USAGE ON SCHEMA public`
  - `GRANT (读写) ON ALL TABLES/SEQUENCES/FUNCTIONS IN SCHEMA public`
（保证本地服务按既有角色能正常跑，不再出现 “permission denied”）

## 验收结果（关键数字）
### 1) 结构版本
- `alembic_version = 20260103_000003`（已对齐新系统）

### 2) 社区池与缓存口径
- `community_pool_total=228`
- `community_pool_active=160`（已把 6 条 paused 真暂停）
- `community_pool_blacklisted=41`
- `paused_but_active=0`
- `community_cache_active=160`
- `cache_active_but_pool_inactive=0`

### 3) 抓取数据量（恢复后）
- `posts_raw_total=195197`
- `posts_raw_current=194635`
- `posts_latest_rows=194635`（MV 正常）
- `comments_total=2063820`

### 4) 向量/评分资产（确认“没丢，只是不满”）
- `post_embeddings_total=186726`
- `post_embeddings_max_post_id=805352`（向量只做到这里，之后的 current 帖还有缺口）
- `current_posts_without_embedding=7951`
- `comment_scores_total=17812`

### 5) 不再自动续跑旧单
- `crawler_run_targets`：`queued/running = 0`

## 下一步（建议，不强制）
1) 如果你要继续跑分析/报告：直接用现在的 `reddit_signal_scanner`（已经切回真实库）。
2) 向量缺口（约 7951 条 current 帖未向量化）：后续按“回填任务”补齐即可（不会影响本次复原正确性）。
3) 旧库 `reddit_signal_scanner_corrupted_20260120_201546` 暂时别删：它是这次事故的对照证据。

