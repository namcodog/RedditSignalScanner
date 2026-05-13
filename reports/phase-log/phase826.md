# Phase 826

## 本轮目标
- 按当前 SOP 完成 2026-04-14 的 15 张日更发布。
- 修复发布后首页显示层回归，确保下次同类发布不再出现 `same_scope_run_max > 2`。

## 发现
- 今天这轮先按 `15-baseline -> freshness gate -> 人工发布面替换` 跑通，得到一版真实可发的 15 张发布面。
- 实际发布完成后，`mini_snapshot` 新 release 首轮 evaluator 出现显示层回归：
  - `front5 = hot / hot / signal / signal / breakdown`
  - `hot_positions = 1 / 2 / 6 / 7`
  - `front9_scope_repeat_count = 0`
  - 但 `scope_run_max = 3`
  - rewrite 原因：`same_scope_run_over_limit`
- 根因不在 publish plan，而在 `mini_snapshot` 的首页显示层重排：
  - 前 9 张交错正常
  - 前 15 张尾部 fallback 会放宽 scope 连续约束
  - 导致尾部可能出现同一 `scope` 连续 3 张

## 修复
- `backend/app/services/hotpost/mini_snapshot.py`
  - 在现有 `_reorder_display_window()` 后新增 `_repair_display_scope_runs()`
  - 只对首页前 15 张尾部做最小修复
  - 不改前 5 模式、不改前 9 交错、不改低层选卡
  - 当检测到 `scope_run_max > 2` 时，只在前 15 张第 10 位之后尝试局部换位，直到 run 降回 `<= 2`
- `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`
  - 新增专门覆盖“前 9 正常、尾部 3 连”场景的回归测试
  - 确保修复后仍保持：
    - `front5 = hot / hot / signal / signal / breakdown`
    - `hot_positions = 1 / 2 / 6 / 7`
    - `scope_run_max <= 2`

## 发布与验证
- 代码回归：
  - `cd backend && python -m py_compile app/services/hotpost/mini_snapshot.py`
  - `cd backend && pytest tests/scripts/hotpost/test_push_mini_snapshot.py -q --tb=short`
  - 结果：`6 passed`
- 重建快照：
  - `cd backend && python scripts/hotpost/push_mini_snapshot.py`
  - 新 release：`release-d982bc4849eb`
- 发布链一致性：
  - `cd backend && python scripts/hotpost/check_mini_release_sync.py`
  - 结果：
    - `card_count = 200`
    - `feed_contract = 30/30`
    - `cloud_db copy guard = ok`
- 首页显示层 evaluator：
  - `python /Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_homepage_display_order_evaluator_v1.py --input backend/data/hotpost/mini_snapshots/latest.json --window-size 15 --summary-json backend/tmp/homepage-display-order-summary-20260414.json`
  - 结果：
    - `decision = publish`
    - `front5 = hot / hot / signal / signal / breakdown`
    - `hot_positions = 1 / 2 / 6 / 7`
    - `front9_scope_repeat_count = 0`
    - `scope_run_max = 2`
    - `same_event_collision_count = 0`

## 前 15 张摘要
1. `hot | business-growth-ops | paid-economics`
2. `hot | ai-automation | upstream-winds`
3. `signal | ecommerce-sellers | selection-signals`
4. `signal | business-growth-ops | funnel-conversion`
5. `breakdown | ecommerce-sellers | selection-signals`
6. `hot | business-growth-ops | organic-discovery`
7. `hot | ai-automation | upstream-winds`
8. `signal | ecommerce-sellers | selection-signals`
9. `breakdown | business-growth-ops | organic-discovery`
10. `signal | ecommerce-sellers | category-winds`
11. `signal | ai-automation | tools-efficiency`
12. `signal | business-growth-ops | paid-economics`
13. `signal | ai-automation | agent-builder`
14. `signal | ai-automation | agent-builder`
15. `signal | ecommerce-sellers | kill-signals`

## 结论
- 今天这轮 15 张已经真实发布，不是 dry-run。
- 发布后的首页显示层回归已经修复，并且补了专门的回归测试。
- 当前显示层 winner 重新回到 `publish`，后续同类发布不应再因尾部 `scope` 三连而掉回 `rewrite`。
