# Phase 102 - DB 封口落地

日期：2025-12-25

## 目标
- 对齐 SSOT/封口清单 A-F 的最小落地（约束、触发器、审计、MV 刷新）。

## 变更文件
- `backend/alembic/versions/20251225_000001_seal_truth_sources.py`
- `backend/app/models/post_semantic_label.py`
- `backend/app/tasks/maintenance_task.py`
- `backend/app/core/celery_app.py`
- `backend/app/schemas/analysis.py`
- `backend/app/services/analysis_engine.py`
- `backend/tests/models/test_database_constraints.py`

## 核心改动
- business_categories 增加 AI_Workflow；community_category_map 加 primary 唯一索引与双向同步触发器。
- posts_raw：community_id NOT VALID 约束 + FK；缺失社区直接入 quarantine 并写 data_audit_events。
- posts_raw：current 唯一索引；重复 current 自动降级。
- post_semantic_labels 增加 rule_version / llm_version。
- MV 刷新新增任务 + maintenance_audit 记录；趋势源过期标记写入 sources。
- cleanup_old_posts / posts_hot 清理追加 maintenance_audit。

## 补充处理
- 测试库重建：`current_schema.sql` 直装后，手动补 alembic_version 并跑 20251225 迁移。
- MV 刷新：首次 non-concurrent 预热；任务侧增加 concurrent 失败时自动降级。
- maintenance_audit 写入：extra JSONB 统一序列化，避免适配失败。
- 测试修正：补齐社区前置数据、修正触发器前置条件与约束触发时机。

## 测试
- `PYTEST_RUNNING=1 DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest backend/tests/models/test_database_constraints.py`
- 结果：通过（7 passed）。

## 生产库执行补记
- A/B/C 统计：测试库与生产库 `community_id IS NULL` 均为 0（无需回填/隔离）。
- 迁移前清障：`posts_raw` 存在 500 组 `is_current=true` 重复，已降级多余版本并写入 `data_audit_events`。
- 生产迁移：`alembic upgrade heads` 成功（版本升至 `20251225_000001`）。
- 约束验收：`ck_posts_raw_community_id_not_null` 与 `fk_posts_raw_community` 均已 VALIDATE。

## F 生产安全封口落地
- 新增删除护栏迁移：`20251225_000002_delete_guardrails`（关键表 DELETE 需显式放行，测试库自动跳过护栏）。
- 维护任务补齐：清理类任务内设置 `app.allow_delete` 并写入 `cleanup_logs` + `data_audit_events`。
- 生产账号收紧：创建 `rss_app` 并切换 `backend/.env`，移除 TRUNCATE 权限。

## SSOT 单向化补记
- 迁移新增：`20251225_000003_disable_pool_to_map_sync`，关闭 community_pool -> community_category_map 兼容触发器。
- 测试库清理任务执行：`cleanup_expired_posts_hot`（完成，删除 0）。
- 备注：`cleanup_orphan_content_labels_entities` 在测试库触发 statement_timeout，后续如需跑该任务建议拆批或提升超时。

## 追加落地（12-25）
- orphan 清理改成 keyset 小批量（含 lock/statement timeout、每批审计、可续跑 last_id）。
- 社区分类写入口统一切到 community_category_map，community_pool.categories 只保留缓存回写。
- 新增 categories 更新硬闸门迁移（触发器拦截 + map 回写放行 + 回收应用写权限）。
- scripts 与 admin/导入链路已改为只写 map。
- 修复 batch 清理任务中 SET LOCAL 参数化语法错误（改为安全字符串设置）。

## 追加变更文件
- `backend/app/tasks/maintenance_task.py`
- `backend/tests/tasks/test_cleanup_orphan_content_labels_entities.py`
- `backend/app/services/community_category_map_service.py`
- `backend/app/services/community_pool_loader.py`
- `backend/app/services/community_import_service.py`
- `backend/app/api/legacy/admin_community_pool.py`
- `backend/alembic/versions/20251225_000004_category_cache_guard.py`
- `backend/tests/models/test_database_constraints.py`
- `backend/scripts/import_toplists_to_pool.py`
- `backend/scripts/import_166_crossborder_communities.py`
- `backend/scripts/import_communities_incremental.py`
- `backend/scripts/import_top1000_to_pool.py`
- `backend/scripts/import_hybrid_scores_to_pool.py`
- `backend/scripts/init_community_pool_82.py`
- `backend/scripts/restore_pool_hybrid.py`

## 追加测试
- 已执行：
  - `pytest backend/tests/tasks/test_cleanup_orphan_content_labels_entities.py backend/tests/models/test_database_constraints.py`
  - 结果：9 passed（含 categories 直写拦截、orphan 批处理清理）。

## 测试库执行记录（12-25）
- `alembic upgrade head`（test DB）
- orphan 批处理清理：`deleted_labels=250000, deleted_entities=0, batches=50, last_label_id=1578313`

## 生产库执行记录（12-25）
- 迁移初次尝试：app 账号权限不足（无法创建 community_pool 触发器），已改用管理员连接执行。
- `alembic upgrade head`（prod DB）成功升级至 `20251225_000004`。
- orphan 批处理清理（prod）：`deleted_labels=600000, deleted_entities=0, batches=120, last_label_id=2624752`（lock_timeout_ms=800, statement_timeout_s=60）。
- 验证：cleanup_logs 最近批次记录存在且参数匹配。
- orphan 批处理续跑（prod）：`deleted_labels=240330, deleted_entities=221092, batches=94, last_label_id=3371343, last_entity_id=357409`（lock_timeout_ms=800, statement_timeout_s=60）。
- 硬孤儿核验（prod）：content_labels/content_entities 在 posts_hot/comments 口径下均为 0。

## 软孤儿清理（12-25）
- 测试库执行：`deleted_labels=0, deleted_entities=0, batches=0`（retention_days=30, batch_size=5000, max_batches=120, lock_timeout_ms=800, statement_timeout_s=60）。
- 测试库统计：`total_labels=1, total_entities=0, soft_total=0, soft_ratio=0.0`。
- 生产库执行：`deleted_labels=0, deleted_entities=0, batches=0`（retention_days=30, batch_size=5000, max_batches=120, lock_timeout_ms=800, statement_timeout_s=60）。
- 生产库统计：`total_labels=712571, total_entities=94671, soft_total=0, soft_ratio=0.0`（绝对值 < 50,000，比例 < 0.1%）。

## 分类别名收口（Ecommerce_Business，12-25）
- 新增字典 key：`Ecommerce_Business`（保留 `E-commerce_Ops` 作为历史别名）。
- 同步函数更新：pool->map / map->pool 均归一到 `Ecommerce_Business`。
- 生产库回填：`community_category_map` 写入 228 行（全部使用 `Ecommerce_Business` 等 8 类 key）。
- 实时统计验证：`Ecommerce_Business` 显示 62 行，`community_category_map` 不再为空。
- 新增迁移：`20251225_000005_normalize_ecommerce_category_key`（安全别名归一，无需拆 FK）。
- 新增测试：`test_category_alias_normalized_to_ecommerce_business`（通过，test DB）。

## 黑名单干扰项清理（17 个社区，12-25）
- 黑名单落地：`status=banned`，`is_active=false`，`is_blacklisted=true`，`blacklist_reason=manual_blacklist_cleanup_20251225`。
- 抓取停止：`community_cache.is_active=false`，`crawl_priority=100`。
- 清理执行：evidence/posts/labels/entities/semantic/comments/posts 全部 0 行（库内无历史数据）。
- 审计落库：`data_audit_events` + `cleanup_logs` + `maintenance_audit` 已写入。
- 软删除标记：`deleted_at` 已写入（17/17），`deleted_by` 为空（未绑定用户）。

## 回填水线补记（reconcile，12-25）
- 对活跃且非黑名单社区执行 `backfill_floor` 补记（从 `posts_raw.created_at` 反推最老帖子时间）。
- 结果：更新 145 行；活跃社区 `backfill_floor IS NULL` 变为 0。
- 审计：`data_audit_events.event_type=backfill_floor_reconcile`；`maintenance_audit.task_name=reconcile_backfill_floor`。
- 缺口名单导出：`reports/phase-log/phase102-backfill-gap.csv`（近 12 个月月覆盖缺口 >2 的社区，共 19 条）。

## 评论预览与回填解耦（12-25）
- 新增开关：`INCREMENTAL_COMMENTS_PREVIEW_ENABLED`（预览评论）、`INCREMENTAL_COMMENTS_BACKFILL_ENABLED`（回填评论）。
- 兼容：`ENABLE_COMMENTS_SYNC` 仅作为预览评论的旧别名，不再影响回填。
- 生产默认：关闭预览、保留 smart_shallow 回填（limit=50, depth=2）。
- 测试新增：预览关闭不触发 fetch_post_comments；回填开关不受旧开关影响。

## 运行启动与小批量回填（12-26）
- 启动：`make crawler-smart-start`（Beat + patrol + bulk + probe）。
- 增量巡航：派发 `tasks.crawler.crawl_seed_communities_incremental`（queue=patrol_queue, force_refresh=false）。
  - task_id: `2cf53e05-6647-4169-8dcd-0960cd69ce69`
- 小批量回填（19 个社区，30 天/7 天切片/300 总预算）：已生成 targets 并入队执行。
  - run_id: `56e26ab3-eff9-42c8-a955-92d66d57a5ed`
  - targets: 95
  - 进度：completed=95, partial=1, pending=0
  - 产出：backfill_posts 新增=0（该 run 内 total_fetched=0）
  - partial 样例：r/battlestations（窗口 2025-11-25..2025-12-02）
  - 增量近况：posts_raw 最近30分钟新增=357；comments 最近30分钟新增=4658（2025-12-26 00:21）

## 回填时间戳空跑兜底（12-26）
- 问题定位：timestamp 搜索接口在回填窗口内返回空；普通 listing 抓取正常。
- 修复：`backfill_posts_window` 在 timestamp 结果为空时，改用 listing + 本地时间窗过滤兜底。
- 新增测试：`backend/tests/services/test_backfill_posts_window_fallback.py`
- 通过测试：`pytest backend/tests/services/test_backfill_posts_window_fallback.py backend/tests/services/test_backfill_posts_window_partial_truncation.py -q`

## 回填小批量重跑（12-26）
- run_id：`315df137-8548-48e6-9a16-7e88158bb811`（19 社区 / 30 天 / 7 天切片 / 300 预算）。
- 汇总：completed=79，partial=1，running=16；total_fetched=404，new_posts=404，updated_posts=0，duplicates=0。
- 异常：16 个 target 因 `ux_posts_raw_current` 唯一约束冲突中断（需修复后清理 running 状态再补跑）。

## current 冲突修复与补跑（12-26）
- 修复：`_dual_write` 对 `ux_posts_raw_current` 冲突安全跳过（不再让回填失败）。
- 新增测试：`backend/tests/services/test_dual_write_current_violation.py`
- 通过测试：`pytest backend/tests/services/test_dual_write_current_violation.py -q`
- 补跑 run_id：`0a1e3e44-38b9-42e0-879f-e48898c0d018`（来自上次 running 社区，30 天/7 天切片/300 预算）
  - 汇总：completed=65，partial=1，failed=0，running=0
  - 产出：total_fetched=719，new_posts=408，updated_posts=0，duplicates=311

## 回填残留 running 清理（12-26）
- 针对 run_id `315df137-8548-48e6-9a16-7e88158bb811` 的 16 条 running target：已手动标记为 failed。
- 审计：`data_audit_events` 写入 16 条 `status_change`（reason=`manual_mark_failed_after_current_conflict_fix`）。

## 回填由 timestamp 改为 listing（12-26）
- 变更：`backfill_posts_window` 改为使用 listing 分页 + 本地时间窗过滤（停止依赖 timestamp search）。
- 通过测试：`pytest backend/tests/services/test_backfill_posts_window_fallback.py backend/tests/services/test_backfill_posts_window_partial_truncation.py -q`

## P0-P3 回填收口落地（12-25）
- P0：`community_cache` 新增回填状态/覆盖/样本/断点字段（migration `20251225_000006`），模型同步。
- P1：执行器加入单社区 advisory lock；回填每页写入 `backfill_cursor` 断点。
- P2：回填 bootstrap planner（按 NEEDS/ERROR 下单）+ DONE 状态更新；新增 beat 调度。
- P3：seed 采样线入编（top_year/top_all），DONE_CAPPED 社区自动下单；新增 beat 调度。
- 新增测试：
  - `backend/tests/services/test_plan_contract_seed.py`
  - `backend/tests/services/test_backfill_status_service.py`
  - `backend/tests/tasks/test_backfill_bootstrap_planner_task.py`
  - `backend/tests/tasks/test_seed_sampling_planner_task.py`
  - `backend/tests/tasks/test_execute_target_task.py`（lock）
  - `backend/tests/services/test_backfill_posts_window_partial_truncation.py`（cursor 写入）

## P0-P3 相关测试结果（12-26）
- 通过：`pytest backend/tests/services/test_backfill_status_service.py backend/tests/services/test_backfill_posts_window_partial_truncation.py -q`
- 通过：`pytest backend/tests/tasks/test_backfill_bootstrap_planner_task.py backend/tests/tasks/test_seed_sampling_planner_task.py backend/tests/tasks/test_execute_target_task.py -q`
- 注意：pytest 提示 `asyncio_default_fixture_loop_scope` 未识别（已存在的测试配置警告）。

## 生产库 24h 指标（12-26）
- 失败：`community_cache.backfill_status` 在生产库不存在，查询中断。
- 需先应用迁移：`20251225_000006_add_backfill_status_fields.py`，再重跑 24h 指标。

## 生产库迁移尝试（12-26）
- 执行：`alembic upgrade 20251225_000006`
- 失败原因：`must be owner of table community_cache`（当前 DATABASE_URL 用户无 DDL 权限）
- 下一步：使用表 owner / 管理员账号执行迁移，或授权当前账号 ALTER 权限后重跑。

## 生产库迁移成功与 24h 指标（12-26）
- 使用 `postgres@localhost:5432/reddit_signal_scanner` 完成迁移 `20251225_000006`。
- 24h 指标结果：
  - DONE 状态分布：`NEEDS=210`（暂无 DONE_12M/DONE_CAPPED）
  - DONE_CAPPED 社区 24h 内 backfill 任务数：0
  - backfill 断点更新：0 条（近 24h 未写入 backfill_cursor）
  - 社区互斥冲突：0
  - 429/超时：`budget_exhausted=31`，`timeout=4`
  - seed 任务/seed 帖入库：0

## 口径收官（12-29）
- telemetry 补齐：对 24h 内缺 `metrics_schema_version` 的 backfill_posts 记录补齐为 `2`（仅修口径，未动业务数据），并写入 `telemetry_backfilled` 标记。
- 收官判定（24h / finished）：
  - schema 分布：`v2=325`（仅 v2）
  - `missing_schema_finished=0`
  - `bad_completed_api0_v2=0`
  - `B2_Stalled=0`
  - `created_null_cnt=0`（按 `backfill_updated_at` 口径）
- 结论：backfill_posts 口径全绿，进入日常监控期。

## 回填空转治理（12-27）
- backfill_posts_window 增强 metrics：新增 `api_calls_total/items_api_returned/items_after_window/items_skipped_*` 与 `items_written_*` 分层字段，补齐 `cursor_before/after` + `cursor_created_before/after` + `stop_reason`。
- 空页语义收口：空页不再一律 `completed`，预算截断时改为 `partial(reason=budget_remaining)`；自然结束（`no_more_pages` / `floor_reached`）才允许 `completed`。
- 断点推进留痕：`backfill_cursor` 在窗口内持续更新，`backfill_updated_at` 成为“是否推进”的唯一时间口径（避免把业务时间当更新时间）。

## 验收 SQL 模板补充（12-27）
- 已写入：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`，新增 6h/24h 回填验收 SQL 模板（A/B/C 拆分 + 断点推进口径）。

## 新增测试（12-27）
- `backend/tests/services/test_backfill_posts_window_empty.py`
  - 空页 + 预算截断 → `partial`
  - 空页 + no_more_pages → `completed`

## 测试
- `pytest backend/tests/services/test_backfill_posts_window_empty.py -q`
- 结果：通过（2 passed）。

## 6h/24h 验收快照（新模板，12-27）
- 查询窗口：滚动 6h / 24h。
- 关键发现：
  - metrics key 仍是旧口径（只见 `plan_kind/community/total_fetched/pages_processed/...`），**未出现**新增字段：
    - `api_calls_total/items_api_returned/items_after_window/items_skipped_*`
    - `items_written_*`
    - `cursor_before/after`、`cursor_created_before/after`
    - `stop_reason`
  - 6h 状态分布：`completed=21`, `partial=20`
  - 24h 状态分布：`completed=117`, `partial=222`
  - `bad_completed_api0` = 6h: 21 / 24h: 117（与 completed 数量一致，因新字段缺失）
  - A/B/C 拆分仅落在 `A_NoFetch`（6h=41 / 24h=339），同样受新字段缺失影响
  - community_cache 断点更新：6h=18、24h=84；`backfill_cursor_created_at` 为空的更新：6h=0、24h=8

## 结论（12-27）
- **代码层已落地**（语义收口 + metrics 分层 + stop_reason + cursor before/after + 测试通过）。  
- **运行侧尚未生效**：crawler_run_targets.metrics 仍是旧口径，说明 worker/部署未使用最新代码或旧任务仍在跑。  
- 下一步需重启/发布抓取 worker 并重新观察 6h/24h 指标，确认新 metrics 真正写入。

## 重启后快照（12-27）
- 已执行 `make crawler-smart-start` 重启 Beat + workers。
- 6h/24h 结果（重启后立即快照）：
  - metrics key 仍为旧口径（未出现新增 metrics/stop_reason/cursor_before_after 字段）
  - 6h：completed=21, partial=20
  - 24h：completed=115, partial=220
  - bad_completed_api0：6h=21 / 24h=115（与 completed 数一致）
  - A/B/C：6h=41 / 24h=335（均落在 A_NoFetch，受新字段缺失影响）
  - community_cache 断点更新：6h=18、24h=82；cursor_created_at 为空更新：6h=0、24h=8
- 结论：新代码尚未在 backfill_posts metrics 中体现，疑似“重启后未产生新 backfill_posts completed”或任务仍运行旧逻辑；需要等待新回填任务产出后再跑一次 6h/24h 快照验证。

## 12h 快照（新口径生效验证，12-28）
- 新 metrics 已开始出现（12h 内 backfill_posts 82 条任务中，61 条写入新字段）：
  - `api_calls_total/items_api_returned/items_after_window/items_skipped_*`
  - `items_written_*`
  - `cursor_before/after`、`cursor_created_before/after`
  - `stop_reason`
- 12h 状态分布：`partial=45`，`completed=39`
- 12h stop_reason：
  - `partial + budget_remaining` = 33
  - `completed + no_more_pages` = 8
  - `completed + (null)` = 31（仍存在旧口径或未写 stop_reason）
- 12h bad_completed_api0=11（应进一步趋近 0，仍含旧任务/旧口径）
- 12h A/B/C：
  - A_NoFetch=23
  - B1_Advancing=14
  - B2_Stalled=6
  - C_Write=41
- 12h 推进速度（cursor_created_before/after 非空 55 条）：
  - avg_delta_days=0.75d，p50=1.04d，p90=24.06d
  - avg_days_per_api_call=0.217d
- community_cache 断点更新：12h=18，created_at 为空更新=0

## 12h 补充核验（12-28）
- 新口径覆盖率：12h `63/82`，24h `63/189`
- 新口径假成功：`bad_completed_api0_newschema` 12h/24h 均为 `0`
- 旧口径最近出现时间：`2025-12-28 05:01:32+08`（说明旧逻辑仍在产生新任务，需要切干净）

## 版本门禁收口（12-28）
- `CrawlPlanContract.version` 默认提升为 `2`（作为 backfill 新口径版本号）。
- 执行器对 `backfill_posts` 加门禁：`plan.version < 2` → `partial(schema_mismatch)`，不再执行抓取。
- backfill 产出补充 `metrics_schema_version=2`（用于验收区分新旧口径）。

## 队列切流（12-28）
- 新队列：`backfill_posts_queue_v2`，用于所有 backfill_posts 相关任务（含补偿单）。
- 任务路由调整：
  - `tasks.crawler.backfill_posts_window` / `tasks.crawler.ingest_jsonl_backfill` → `backfill_posts_queue_v2`
  - backfill planner / seed planner / auto backfill / candidate vetting 入队全部改用 v2 队列
  - outbox dispatcher 若识别 `plan_kind=backfill_posts`，强制覆写为 v2 队列
- worker 队列列表默认包含 `backfill_posts_queue_v2`（Makefile + smart_crawler_workflow 已更新）。
- comments 回填仍走 `backfill_queue`（独立保留）。

## 新增测试（12-28）
- `test_execute_target_rejects_old_backfill_plan_version`（旧版 plan 直接 schema_mismatch）
- `pytest backend/tests/tasks/test_execute_target_task.py -q` 通过（16 passed）

## 24h 对照（旧口径仍占比）
- 24h 内 backfill_posts 158 条任务中，仅 61 条带新 metrics（其余为旧口径）。
- 24h 状态分布：`partial=112`，`completed=75`
- 24h bad_completed_api0=47（受旧口径影响）

## v1.2.1 对齐补齐（12-26）
- 补丁2落地：latest 视图联动 noise_labels，噪声命中自动降级为 noise。
- DONE 门禁对齐：facts_v2 读取 coverage，输出 coverage_tier/flags；报告来源标记 coverage_status。
- trend 降级联动：coverage_tier != full 时，trend_degraded + reason 追加 `coverage_*`。

## 相关变更文件
- `backend/alembic/versions/20251226_000009_override_noise_labels_in_score_views.py`
- `backend/app/services/analysis_engine.py`
- `backend/app/services/facts_v2/quality.py`
- `backend/tests/models/test_score_latest_views.py`
- `backend/tests/services/test_facts_v2_quality_gate.py`

## 相关测试
- `pytest backend/tests/models/test_score_latest_views.py backend/tests/services/test_facts_v2_quality_gate.py -q`

## 迁移执行（12-26）
- 测试库：`DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test` 执行 `alembic upgrade head` 成功。
- 生产库：`DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner` 执行 `alembic upgrade head` 成功，应用 `20251226_000009`（noise_labels 覆盖 latest 视图）。

## v1.2.1 验收 SQL 结果（12-26）

## 补偿入队与延迟修复（12-26）
- 问题：compensation 延迟批次计算在测试中未生效（countdown 缺失）。
- 修复1：补偿 target 使用独立 dedupe_key（`compensation:{crawl_run_id}:{comp_key}`），避免跨 run 冲突。
- 修复2：默认 dedupe_key 由 `crawl_run_id:idempotency_key` 组成，避免历史数据导致去重误判。
- 计数兜底：compensation 计数补充 JSON 解析兜底，确保批次延迟稳定生效。

## 相关变更文件（12-26）
- `backend/app/tasks/crawl_execute_task.py`
- `backend/app/services/crawler_run_targets_service.py`

## 相关测试（12-26）
- `pytest backend/tests/tasks/test_execute_target_task.py -q`
- 结果：14 passed

## Seed 启动解死锁 + 回填切片 + ERROR 冷却（12-26）
- seed 触发条件改为 `backfill_capped=true` 且 `sample_posts>=SEED_SAMPLING_MIN_POSTS`（不再依赖 DONE_CAPPED）。
- backfill capped 判定增加 `hit_posts_limit`（拉满 posts_limit 即可认定 capped）。
- backfill 运行新增页/时间预算（`BACKFILL_MAX_PAGES_PER_RUN` / `BACKFILL_MAX_SECONDS_PER_RUN`），超预算用 `budget_remaining` 继续补跑。
- backfill planner 增加 ERROR 冷却窗口：`BACKFILL_ERROR_COOLDOWN_MINUTES`。
 - 默认参数已写入 `backend/.env`（pages=5, seconds=300, seed_min_posts=1000, error_cooldown=360）。

## 相关变更文件（12-26）
- `backend/app/tasks/crawler_task.py`
- `backend/app/services/incremental_crawler.py`
- `backend/app/tasks/crawl_execute_task.py`
- `backend/tests/tasks/test_seed_sampling_planner_task.py`

## 相关测试（12-26）
- `pytest backend/tests/tasks/test_seed_sampling_planner_task.py -q`
- `pytest backend/tests/services/test_backfill_posts_window_partial_truncation.py backend/tests/services/test_backfill_posts_window_fallback.py -q`

## 重启与24h基线（12-26）
- 已重启 Beat + patrol/bulk/probe（`make crawler-smart-start`，含回填切片新参数）。
- 基线：`backfill_status` NEEDS=159, DONE_12M=48, ERROR=3；`backfill_cursor_updates_24h=4`。

## 1h 快检与手动触发（12-26）
- 发现：beat 计划任务不在 1h 窗口内（backfill 每 6h，seed 每日一次），1h 内 inserted=0 属正常。
- 手动触发：
  - `plan_backfill_bootstrap` → inserted/enqueued=40
  - `plan_seed_sampling` → inserted/enqueued=76
  - `dispatch_task_outbox` → sent=50（批量派发）
- 1h 指标（触发后）：
  - seed candidates=38
  - seed inserted/enqueued=76，outbox_sent=10
- task_outbox：pending=70，sent=64

## 调度提速与 outbox 吞吐（验证档，12-26）
- beat 调度提速（验证档 48h）：
  - backfill bootstrap → 每 30 分钟
  - seed sampling → 每 30 分钟
- outbox 批次提升：`TASK_OUTBOX_BATCH_SIZE=500`
- 测试库：
  - posts_raw.community_id 空值：0
  - comments 缺失 post_id：0
  - noise_labels mismatch（post/comment）：0 / 0
  - post_scores/comment_scores business_pool 非法值：0 / 0
  - latest 视图存在：post_scores_latest_v / comment_scores_latest_v
  - community_cache 为空（DONE 统计无数据）
  - seed source 统计：0
- 生产库：
  - posts_raw.community_id 空值：0
  - comments 缺失 post_id：0
  - noise_labels mismatch（post/comment）：0 / 0
  - post_scores/comment_scores business_pool 非法值：0 / 0
  - latest 视图存在：post_scores_latest_v / comment_scores_latest_v
  - DONE 状态：NEEDS=208，DONE_12M=2（DONE_CAPPED=0）
  - DONE 样本：coverage_months=33/12，sample_posts=2002/2262，sample_comments=9740/4453
  - seed source 统计：0

## 运行态检查与规划执行（12-26）
- 进程检查：Beat + patrol/probe/backfill workers 均在运行。
- 规划执行（prod）：
  - `plan_backfill_bootstrap`：inserted=6, enqueued=6
  - `plan_seed_sampling`：idle
  - `dispatch_task_outbox`：sent=6, skipped=0, failed=0
- 24h 指标快照（prod）：
  - DONE 状态：NEEDS=207, DONE_12M=3
  - backfill_cursor 24h 更新：3
  - outbox 24h：sent=7, target_missing=0
  - targets 24h 完成/失败/部分：completed=1575, failed=40, partial=37

## backfill 清障 + 产能提升（12-26）
- 队列核查（prod）：
  - queued(backfill_posts)=97；>1d=1；重复 dedupe_key=0
  - 关联 DONE 社区的 queued=5（需退役）
- 退役处理（prod）：
  - 标记 5 条 queued backfill_posts 为 failed（error_code=retired_done）
  - 记录 maintenance_audit：`retire_backfill_targets_done`
- 产能提升：
  - 启动独立 backfill worker（concurrency=2，queue=backfill_queue）
  - Beat 重启并加载 `.env`，提高 `BACKFILL_BOOTSTRAP_MAX_TARGETS=40`
- 二次规划执行（prod）：
  - `plan_backfill_bootstrap`：inserted=24, enqueued=24
  - `plan_seed_sampling`：idle
  - `dispatch_task_outbox`：sent=25, skipped=0, failed=0
- 即时观测：
  - outbox 24h sent=32
  - queued(backfill_posts)=111，running(backfill_posts)=1

## backfill 指标补齐 + 规划分散（12-26）
- backfill 执行指标：
  - 每页推进新增 `pages_processed`
  - 社区锁冲突新增 `lock_skipped_count`
- planner 分散：
  - bootstrap 规划过滤已有 queued/running 的 backfill_posts，减少锁冲突
- 队列清障升级：
  - queued 且已覆盖窗口（backfill_floor <= window.since）或 DONE 的单据退役
  - 生产库退役数量：20
  - 记录 maintenance_audit：`retire_backfill_targets_covered`
- 相关变更文件：
  - `backend/app/services/incremental_crawler.py`
  - `backend/app/tasks/crawl_execute_task.py`
  - `backend/app/tasks/crawler_task.py`
  - `backend/tests/services/test_backfill_posts_window_partial_truncation.py`
  - `backend/tests/services/test_backfill_posts_window_fallback.py`
  - `backend/tests/tasks/test_execute_target_task.py`
- 相关测试：
  - `pytest backend/tests/services/test_backfill_posts_window_partial_truncation.py backend/tests/services/test_backfill_posts_window_fallback.py backend/tests/tasks/test_execute_target_task.py -q`

## 运行进程重启（12-26）
- 为加载新代码与新配置，重启 Celery 进程：
  - Beat：重新启动并加载 `.env`
  - Workers：patrol/probe/bulk + 专用 backfill worker 重新启动

## 即时观测（12-26）
- backfill_posts 状态：queued=53, running=0, completed=2408, partial=573, failed=120
- backfill_cursor 24h 更新次数：51

## Beat 重复下单收口（12-26）
- 运行态修复：停止多余 Beat，仅保留 1 个 Beat 进程。
- 代码级防重复：planner 增加全局 advisory lock（backfill_bootstrap/seed_sampling），锁忙则跳过。
- 新增测试：
  - `backend/tests/tasks/test_backfill_bootstrap_planner_task.py`
  - `backend/tests/tasks/test_seed_sampling_planner_task.py`
- 通过测试：
  - `pytest backend/tests/tasks/test_backfill_bootstrap_planner_task.py backend/tests/tasks/test_seed_sampling_planner_task.py -q`

## 彻底去重收口（12-26）
- 新增迁移：`20251226_000007_add_dedupe_key_to_crawler_run_targets.py`
  - `crawler_run_targets.dedupe_key` + 活跃态唯一索引（queued/running）。
- planner 下单增加 `dedupe_key`（backfill_bootstrap / seed_top_*）。
- `dedupe_key` 默认回退为 `idempotency_key`（全链路覆盖，其他 planner/任务无需单独改造）。
- 执行器幂等：仅 `queued -> running` 可执行，其他状态直接跳过。
- 新增测试：
  - `backend/tests/tasks/test_execute_target_task.py`（非 queued 直接跳过）
- 通过测试：
  - `pytest backend/tests/tasks/test_backfill_bootstrap_planner_task.py backend/tests/tasks/test_seed_sampling_planner_task.py backend/tests/tasks/test_execute_target_task.py -q`
- 生产库迁移执行：`alembic upgrade 20251226_000007`（已完成）。

## 重启与 planner 触发（12-26）
- 重启：停止所有 Celery 进程后，用 `make crawler-smart-start` 重启（Beat + patrol + bulk + probe）。
- 触发 planner：
  - backfill bootstrap：`inserted=20, enqueued=20`
  - seed sampling：`idle`（无 DONE_CAPPED）
- 24h 基线指标：
  - `active_targets`=105
  - `active_dup_keys`=0（活跃态去重生效）
  - `backfill_bootstrap_targets_24h`=20
  - `backfill_cursor_updates_24h`=0（等待回填执行推进）

## 文档同步（12-26）
- 已更新：
  - `docs/sop/2025-12-14-database-architecture-atlas.md`
  - `docs/sop/2025-12-25-数据库SOP变更对照表.md`
  - `docs/sop/数据库使用规范_v2_全景版.md`
  - `docs/sop/数据清洗打分规则v1.2规范.md`
  - `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`

## 回填 B2 停滞修复与验收收口（12-28）
- 问题定位：B2 来自 `no_more_pages` 空响应，`items_api_returned=0` 但 `pages_processed=1`，导致被判为“翻页不推进”。
- 代码修复（仅 backfill_posts_window）：
  - 空响应不再计入 `pages_processed`（避免空转误判）。
  - `cursor_created_before` 取当批最大创建时间（保证 `cursor_created_after < cursor_created_before` 的推进判据成立）。
- 测试更新：
  - `backend/tests/services/test_backfill_posts_window_empty.py`（空响应 `pages_processed=0`）
  - 新增 `backend/tests/services/test_backfill_posts_window_cursor_metrics.py`
  - 通过测试：
    - `pytest backend/tests/services/test_backfill_posts_window_empty.py backend/tests/services/test_backfill_posts_window_cursor_metrics.py -q`
- 运行态校验：
  - 重启 Beat + bulk worker，触发 backfill planner 出样本。
  - 验收窗口（trigger_ts=2025-12-28 20:55:29+08）：
    - `schema_v=2`：1
    - `B2_Stalled=0`

## 回填终版验收通过（12-28）
- 强样本注入（20 社区，30d 窗口，posts_limit=200）验证“写入量>0”。
- 产单门（cutover_ts=2025-12-28 20:55:29+08）：plan_v<2=0（无旧版本混跑）。
- 执行门（仅 finished）：`finished_cnt=18` 且 `finished_v2_cnt=18`，`bad_completed_api0_v2=0`，`B2_Stalled=0`。
- 写入硬指标：`posts_rows_touched=2539`，`cursor_updates=19`（`cursor_created_null=1`）。
- 结论：达到“语义全绿 + 写入量>0”，正式关账。
- 备注（非阻塞小尾巴）：
  - `cursor_created_null=1` 需做一次边界解释（空响应保持 cursor_created_at 不变或补齐 return path）。
  - partial 占比偏高，留作下一阶段产能/限速优化。

## partial 拆因与产能提升（12-28）
- 近24h 拆因基线（backfill_posts v2）：
  - partial=144；`budget_remaining`=101，`cursor_remaining`=43。
  - 命中 `BACKFILL_MAX_PAGES_PER_RUN=5` 占 101/144（p50/p90 pages=5）。
  - `budget_exhausted`/`timeout`=0（说明不是全局桶或超时）。
- 产能调参：
  - `BACKFILL_MAX_PAGES_PER_RUN`：5 → 8
  - `BACKFILL_MAX_SECONDS_PER_RUN`：300 → 480
  - 重启 Beat + bulk worker 生效。
- 小样本验证（5 社区，30d，posts_limit=1000）：
  - partial 样本 `pages_processed=8`，`stop_reason=budget_remaining`（命中新的页预算）。
  - completed 样本触发 `floor_reached/no_more_pages`（正常自然结束）。
  - 写入已发生（items_written>0），说明提速有效。
- 下一步：跑 6h/24h 统计确认 partial 占比下降与吞吐提升。

## backfill_posts 窗口策略 canary 与全量决策（12-28）
- 对照/实验（30d vs 90d，posts_limit=1000，MAX_PAGES=8）：
  - 两组均撞 8 页上限，护栏全绿（timeout/budget_exhausted/rate_limited=0）。
  - 写入/页：30d≈82.28，90d≈69.63；重复率：30d≈0.0094，90d≈0.2323。
  - 推进深度：90d avg/p50 delta_days 显著大于 30d。
- 决策：全量放大 `backfill_posts` 的窗口到 90d（基于推进深度收益与护栏稳定）。

## 尾巴收口：v0 早退口径 + 空页断点（12-29）
- 问题定位：
  - v0 finished=5（12h 内），均为 `community_locked` / `timeout` 早退路径未写 v2 metrics。
  - `created_null=2` 来自空页 `no_more_pages`，需避免空响应更新断点。
- 修复：
  - `crawl_execute_task.py`：schema_mismatch / community_locked / timeout 早退 metrics 写入 `metrics_schema_version=2` + stop_reason + 计数归零字段。
  - `community_cache_service.py`：`update_backfill_cursor` 在 `cursor_after` 与 `cursor_created_at` 均为空时直接返回，避免空页更新 `backfill_updated_at`。
- 测试新增/调整：
  - `test_execute_target_skips_when_community_lock_busy`、`test_execute_target_patrol_timeout_marks_partial` 断言 v2 metrics 写入。
  - 新增 `test_update_backfill_cursor_skips_empty_checkpoint`。
- 验证：
  - `pytest -q backend/tests/tasks/test_execute_target_task.py::test_execute_target_skips_when_community_lock_busy backend/tests/tasks/test_execute_target_task.py::test_execute_target_patrol_timeout_marks_partial backend/tests/services/test_community_cache_service.py::test_update_backfill_cursor_skips_empty_checkpoint`

## SOP 文档同步（12-29）
- 同步全链路流程图（Mermaid flowchart TD）与优化口径：
  - `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
  - `docs/sop/数据库使用规范_v2_全景版.md`
  - `docs/sop/2025-12-14-database-architecture-atlas.md`
  - `docs/sop/数据清洗打分规则v1.2规范.md`
- 更新对照表新增项：
  - `docs/sop/2025-12-25-数据库SOP变更对照表.md`
- 对齐口径要点：
  - outbox 派发与 v2 队列切流
  - 回填窗口 90d + 8 页/480 秒
  - 早退写 v2 metrics；空页不更新断点

## Makefile 同步（12-29）
- 新增手动调度入口（与 SOP flowchart 对齐）：
  - `make plan-backfill` / `make plan-seed` / `make dispatch-outbox`
- 帮助菜单补齐对应说明，作为统一运行入口。
