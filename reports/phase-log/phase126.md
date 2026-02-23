# Phase 126 - Phase102~107 数据库口径核对（Gold/Dev/Test 三库一致性审计）

日期：2026-01-20

## 目标（说人话）
把 Phase102~107 里写死的“数据库合同/口径”拿出来，对照现在本地三库：
- 金库：`reddit_signal_scanner`
- Dev：`reddit_signal_scanner_dev`
- Test：`reddit_signal_scanner_test`

确认：**结构版本一致、关键约束/护栏一致、RLS 不 500、社区池/缓存口径不打架**。

## 我们按 Phase102~107 核对的“关键口径”
### Phase102（DB 封口）
- `posts_raw`：current 唯一索引 `ux_posts_raw_current`，不能再出现重复 current。
- `posts_raw`：`community_id` 非空 + FK（指向 `community_pool.id`）应能 VALIDATE。
- 删除护栏：关键表 DELETE 必须显式放行（`app.allow_delete=1`），测试库自动跳过护栏。
- 分类写入口：以 `community_category_map` 为准，`community_pool.categories` 只做缓存回写（pool→map 兼容触发器应关闭）。

### Phase103/104/105/106（合同 A/B/C + 评论闭环）
- 合同A：RLS/GUC 缺失不许 500（missing_ok=true）；
- 合同B/C：依赖的表/队列账本结构要在 DB 里存在（`tasks/analyses/reports/task_outbox/crawler_runs/crawler_run_targets/facts_snapshots/...`）。

### Phase107（DecisionUnit + semantic_main_view）
- 视图：`semantic_main_view`、`decision_units_v` 必须存在；
- `insight_cards` 必须有 DecisionUnit 承载字段（kind/du_payload 等）；
- `evidences` 必须有 `content_type/content_id`（证据链可审计）；
- `decision_unit_feedback_events` 表必须存在（反馈闭环入口）。

## 核对结果（结论先说）
**口径一致**：三库结构版本一致（到 `20260103_000003`），关键护栏/视图/表都齐全；RLS 缺上下文不会 500；社区池/缓存“暂停/黑名单”口径不打架。

## 关键证据（SQL 核对点）
### 1) 结构版本（Gold/Dev/Test）
- `alembic_version`：三库均为 `20260103_000003`

### 2) Phase102：posts_raw current 唯一
- `dup_current_keys`：Gold/Dev 均为 0（无重复 current）
- `ux_posts_raw_current`：存在（WHERE is_current=true 的唯一索引）

### 3) Phase102：community_id 约束与 FK
核对时发现一处差异（已修掉）：
- 差异：`ck_posts_raw_community_id_not_null` 与 `fk_posts_raw_community` 在 Gold/Dev 中存在但处于 `NOT VALID`（未 validate）。
- 修复：已在 Gold/Dev 立即执行 `VALIDATE CONSTRAINT`。
- 修复后：两条约束 `convalidated=true`，且数据层面 `community_id NULL=0 / invalid FK=0`。

### 4) 删除护栏（Phase102 F）
- `guard_delete_*` 触发器在关键表上存在：`posts_raw/posts_hot/comments/content_labels/content_entities/facts_snapshots/facts_run_logs`。

### 5) 社区分类写入口（SSOT 单向化）
- `community_pool` 上只有 `guard_community_pool_categories_update`
- `community_category_map` 上只有 `sync_pool_categories_from_map`
说明：pool→map 兼容触发器确实已关掉，符合 Phase102 口径。

### 6) 合同A：RLS 不 500
- `pg_policies` 显示：`analyses` 的租户隔离 policy 使用 `current_setting('app.current_user_id', true)`（missing_ok）
- 用 `rss_app` 不设置任何 GUC 直接 `SELECT count(*) FROM analyses;`：返回 0，且**不报错、不 500**。

### 7) 合同B/C：关键账本表存在
`tasks/analyses/reports/task_outbox/crawler_runs/crawler_run_targets/facts_snapshots/facts_run_logs/data_audit_events` 均存在。

### 8) Phase107：DecisionUnit/语义总线结构存在
`semantic_main_view`、`decision_units_v` 视图存在；
`decision_unit_feedback_events` 表存在；
`evidences` 已包含 `content_type/content_id`。

## 当前三库制度（和 Phase102~107 不冲突）
- 金库 `reddit_signal_scanner`：稳定对照底座（不随便写）。
- Dev `reddit_signal_scanner_dev`：本地抓取/回填/分析默认写入（避免污染金库）。
- Test `reddit_signal_scanner_test`：只给测试用（可清空/重建）。

## 下一步
1) 本地跑链路时，确认服务默认连 `reddit_signal_scanner_dev`（避免误写金库）。
2) 如要做“升金”，必须先跑闸门验收（不跑偏/黑名单=0/口径一致），再执行受控升级。

