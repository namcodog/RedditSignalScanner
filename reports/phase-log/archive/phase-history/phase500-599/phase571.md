# Phase 571 - backfill 运行状态双写到 truth-source

## 发现了什么？
- `community_cache` 这边很多字段已经可以接受作为 projection 留着，但 backfill 这条运行状态还差半步：
  - `attempt`
  - `waterline`
  - `backfill_floor`
  - `backfill_cursor`
  - `backfill_status`
- 它们之前主要只写在 `community_cache`，truth-source 的 `community_runtime_state.runtime_notes` 还不够实时。

## 是否需要修复？
- 需要。
- 这不是简单展示字段，而是会影响 runtime 真实判断的运行状态，不应该只停在旧 projection 里。

## 精确修复方法
### 1. 新增 runtime projection 双写服务
- 新增：
  - `backend/app/services/community/community_runtime_projection_service.py`
- 作用：
  - 通过 `community_name` 定位对应的 `community_runtime_state`
  - 把以下运行状态同步写入 truth-source：
    - `last_crawled_at`
    - `last_attempt_at`
    - `last_seen_post_at`
    - `backfill_floor`
    - `runtime_notes.backfill_status`
    - `runtime_notes.backfill_cursor`
    - `runtime_notes.backfill_cursor_created_at`
    - `runtime_notes.coverage_months`
    - `runtime_notes.backfill_capped`
    - `runtime_notes.last_seen_post_id`

### 2. community_cache_service 改成 projection + truth-source 双写
- 更新：
  - `backend/app/services/community/community_cache_service.py`
- 改动：
  - `upsert_community_cache()` 同步 `runtime.last_crawled_at`
  - `mark_crawl_attempt()` 同步 `runtime.last_attempt_at`
  - `update_incremental_waterline_if_forward()` 同步：
    - `runtime.last_seen_post_at`
    - `runtime_notes.last_seen_post_id`
  - `update_backfill_floor_if_lower()` 同步 `runtime.backfill_floor`
  - `update_backfill_cursor()` 同步 checkpoint 到 `runtime_notes`
  - `mark_backfill_running() / mark_backfill_status_only() / update_backfill_status()` 同步 backfill 状态到 `runtime_notes`
  - `update_backfill_status()` 还同步：
    - `runtime.sample_posts`
    - `runtime.sample_comments`

## 验证
- `pytest backend/tests/services/community/test_community_cache_service.py backend/tests/services/crawl/test_backfill_status_service.py backend/tests/services/crawl/test_backfill_posts_workflow.py -q`
  - `8 passed`

## 下一步系统性的计划
- 继续扫剩余 API / report / worker 里还直接拿旧表做正式判断的点
- 重点看：
  - 还有没有只读 `community_cache`、但本质上应该读 `community_runtime_state` 的链路

## 这次执行的价值
- 这一步让 backfill 这条运行状态终于不再只停在旧 projection。
- 现在 truth-source 不只是“配置上是唯一真相源”，而是连 backfill 水位、状态、游标这类 runtime 真状态也开始实时接住了。
