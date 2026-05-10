# Phase 805

## 时间

- 2026-04-14 01:30 CST

## 本轮目标

- 只把 `homepage display-order` 的赢家策略回灌到项目侧
- 不改 `publish plan`
- 不改 prompt
- 不改 named topic 预算
- 不改 schema

## 实际改动

- 修改：
  - `backend/app/services/hotpost/mini_snapshot.py`
- 补测试：
  - `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`

## 回灌内容

- 在现有 `homepage shelf mix` 之后，加一层只作用于首页前 `15` 张的显示层重排
- 规则：
  - 前 `5` 张固定模板：`hot / hot / signal / signal / breakdown`
  - 第 `6-7` 位继续前置剩余 `hot`
  - 前 `9` 张优先交错 `scope`
  - 同一 `scope` 最多连续 `2` 张
  - 同一事件默认不重复霸屏
  - `named topic` 不享受额外显示特权
- 首页前 `15` 张之外不重排，保持原相对顺序

## 验证

- 定向测试：
  - `pytest backend/tests/scripts/hotpost/test_push_mini_snapshot.py -q --tb=short`
  - `5 passed`
- `py_compile`：
  - `backend/app/services/hotpost/mini_snapshot.py`
  - 通过
- 重建 snapshot：
  - 新 release：`release-5d6a952f346a`
- key-os evaluator：
  - `decision = publish`
  - `front5 = hot / hot / signal / signal / breakdown`
  - `hot_positions = 1 / 2 / 6 / 7`
  - `front9_scope_repeat_count = 0`
  - `scope_run_max = 2`
  - `same_event_collision_count = 0`
  - `named_topic_front5_count = 0`

## 当前结论

- `homepage display-order policy` 已正式落地到项目侧
- 当前首页显示顺序已不再是 baseline rewrite，而是 winner keep 方案
- 本轮是纯显示层回灌，没有动低层编排

## 产物

- `backend/tmp/homepage-display-order-summary.json`
- `backend/data/hotpost/mini_snapshots/latest.json`
- `backend/data/hotpost/mini_snapshots/releases/release-5d6a952f346a.json`
