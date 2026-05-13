# Phase 543 - Crawl planner 切到 truth-source

## 时间
- 2026-03-28

## 背景
- `phase542` 已把 Dev 社区层压缩成：
  - `160` 条正式运行社区
  - `18` 条带历史帖子证据的归档社区
- 但 crawl planner 仍直接读取：
  - `community_cache`
  - `community_pool`
- 这会让旧口径继续回流抓取主链，不符合“唯一真相源”收口目标。

## 本轮动作

### 1. 补齐 truth-source runtime 语义字段
- 更新：
  - `backend/app/services/community/truth_source_reconciler.py`
- 在 `community_runtime_state.runtime_notes` 中正式补齐 planner 所需字段：
  - `backfill_status`
  - `coverage_months`
  - `backfill_capped`
  - `backfill_cursor`
  - `backfill_cursor_created_at`
  - `backfill_updated_at`
  - `avg_valid_posts`
  - `quality_tier`

### 2. planner_workflow 切读 truth-source
- 更新：
  - `backend/app/services/crawl/planner_workflow.py`
- 三条 planner 链改成只依赖：
  - `community_registry`
  - `community_runtime_state`
  - `community_domain_membership`
  - `community_governance_decision`
- 具体变化：
  - `backfill bootstrap planner`
    - 读取 `runtime_notes.backfill_status / backfill_cursor / backfill_updated_at`
  - `seed sampling planner`
    - 读取 `runtime_notes.backfill_capped + sample_posts`
  - `low quality planner`
    - 读取 `runtime_notes.avg_valid_posts + last_crawled_at`
- 新规则：
  - 必须是 `registry.is_enabled = true`
  - 必须是 `runtime.is_enabled = true`
  - 必须有 `membership.is_current = true`
  - 必须有 `governance.decision = approved`
- 不再用旧 `community_pool.is_active / is_blacklisted` 做正式放行判断。

### 3. 收紧测试口径
- 更新：
  - `backend/tests/services/crawl/test_planner_workflow.py`
- 测试数据不再靠“只有 cache 就能入 planner”这种旧假设。
- 现在测试样本必须带：
  - 非空业务领域归属
  - truth-source 同步后可生成 membership/governance

## 验证

### 定向测试
- 执行：
  - `pytest backend/tests/services/crawl/test_planner_workflow.py -q`
- 结果：
  - `3 passed`

### Dev 真实回灌
- 执行：
  - `PYTHONPATH=backend DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_dev python3 backend/scripts/community/reconcile_truth_sources.py --json-only`
- 结果：
  - `scanned = 160`
  - `synced = 160`
  - `skipped = 0`

### Dev 核验
- 执行 runtime_notes 检查后确认：
  - `has_backfill_status = 160`
  - `has_backfill_cursor = 160`
  - `has_backfill_capped = 160`
  - `has_avg_valid_posts = 160`

## 结论
- crawl planner 已完成第一段 truth-source 切换。
- 当前正式抓取计划放行不再依赖旧 `community_pool/community_cache`。
- Dev 的 `160` 条正式社区已补齐 planner 所需 runtime 语义字段。
- 旧表继续缩回兼容投影层，不再承担主链正式判断。

## 下一步
1. 继续扫报告/API 侧残留的旧表直接读取点。
2. 只要属于正式判断路径，就继续切到 truth-source。
3. 同步补注释和口径文档，让 AI 与人都不会误读旧表身份。
