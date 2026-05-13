# Phase 542 - Dev 真相源物理压缩完成

## 时间
- 2026-03-28

## 背景
- `phase535` 已把 Dev 社区正式盘恢复到金库运行口径。
- `phase538-539` 已开始把治理与 readiness 主链切到 truth-source。
- 当前剩余阻塞不再是逻辑口径，而是 Dev 社区层物理存量偏胖，仍保留大量 disabled registry / inactive runtime / inactive cache / inactive pool。

## 本轮动作

### 1. 新增压缩服务与脚本
- 新增：
  - `backend/app/services/community/dev_truth_source_compaction_service.py`
  - `backend/scripts/community/compact_dev_truth_source.py`
  - `backend/tests/services/community/test_dev_truth_source_compaction_service.py`

### 2. 固定压缩原则
- 只允许删除：
  - `disabled community_registry`
  - `inactive community_runtime_state`
  - `inactive community_category_map`
  - 无 truth-source 引用的 `inactive community_cache`
  - 无 `posts_raw / community_audit / enabled registry` 引用的 `inactive community_pool`
- 明确禁止：
  - 把归档社区硬映射到 active 社区
  - 删除仍挂着历史帖子证据的 inactive pool
  - 用 fallback 或默认值掩盖引用关系

### 3. 修正压缩统计顺序
- 初版测试暴露一个关键问题：
  - “预估能删多少”与“实际删除顺序”不一致
  - 导致 `inactive pool/cache` 被前置引用错误挡住
- 已修正为按真实删除时序统计：
  1. 先去掉 disabled registry 影响
  2. 再去掉 inactive category map 影响
  3. 再计算最终可删 cache / pool

### 4. 定向测试
- 执行：
  - `pytest backend/tests/services/community/test_dev_truth_source_compaction_service.py -q`
- 结果：
  - `2 passed`

### 5. Dev dry-run
- 执行：
  - `PYTHONPATH=backend DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_dev python3 backend/scripts/community/compact_dev_truth_source.py`
- 产物：
  - `backend/reports/local-acceptance/dev_truth_compaction_1774681335.json`
- dry-run 预估：
  - `deleted_disabled_registry = 73`
  - `deleted_inactive_runtime = 73`
  - `deleted_inactive_category_map = 68`
  - `deleted_inactive_cache = 107`
  - `deleted_inactive_pool = 330`
  - `remaining_archived_pool = 18`
  - `archived_pool_with_posts = 18`

### 6. Dev 真实压缩
- 执行：
  - `PYTHONPATH=backend DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_dev python3 backend/scripts/community/compact_dev_truth_source.py --write`
- 产物：
  - `backend/reports/local-acceptance/dev_truth_compaction_1774681476.json`

## 压缩前后

### 压缩前
- `community_pool.total = 508`
- `community_pool.inactive = 348`
- `community_cache.total = 267`
- `community_cache.inactive = 107`
- `community_registry.total = 233`
- `community_registry.disabled = 73`
- `community_runtime_state.total = 233`
- `community_runtime_state.disabled = 73`
- `community_category_map.total = 228`

### 压缩后
- `community_pool.total = 178`
- `community_pool.inactive = 18`
- `community_pool.effective = 160`
- `community_cache.total = 160`
- `community_cache.inactive = 0`
- `community_cache.active = 160`
- `community_registry.total = 160`
- `community_registry.disabled = 0`
- `community_runtime_state.total = 160`
- `community_runtime_state.disabled = 0`
- `community_category_map.total = 160`
- `archived_with_posts = 18`

## 结论
- Dev 社区层已经从“逻辑恢复但结构偏胖”收成：
  - `160` 条正式运行社区
  - `18` 条带历史帖子证据的归档社区
- 当前这 `18` 条归档 inactive pool 是刻意保留的：
  - 因为仍被 `posts_raw` 历史证据引用
  - 不应该为了表面干净而硬删
- 这轮没有引入任何兜底逻辑，也没有做伪映射。

## 下一步
1. 继续扫描主链里仍直接读 `community_pool / community_cache` 的地方。
2. 把这些正式判断继续切到：
   - `community_registry`
   - `community_domain_membership`
   - `community_governance_decision`
   - `community_runtime_state`
3. 等主链彻底切完，再决定旧表最终保留为兼容投影还是进一步收缩。
