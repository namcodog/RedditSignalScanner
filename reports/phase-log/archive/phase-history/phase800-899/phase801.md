# phase801

## 时间

- 2026-04-13 17:07 CST

## 本轮目标

- 把 `15-baseline` 不只停在 key-os 合同里，而是落实到当前生产默认值。

## 实际改动

- 修改配置：
  - `backend/config/hotpost_supply_discovery_v2.yaml`
  - `operation_defaults.min_cards_per_run: 30 -> 15`
- 修改测试：
  - `backend/tests/services/hotpost/test_workflow_dry_run.py`
  - `backend/tests/services/hotpost/test_offline_publish_plan.py`

## 验证结果

- `pytest backend/tests/services/hotpost/test_offline_publish_plan.py backend/tests/services/hotpost/test_workflow_dry_run.py -q --tb=short`
  - `6 passed`
- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --output backend/tmp/offline-publish-plan-default.json`
  - 默认 `targets.total = 15`
  - 默认 `lane_targets = signal 9 / hot 4 / breakdown 2`
  - 默认 `scope_targets = 5 / 5 / 5`
- 额外核对：
  - `feed_initial_page_size = 30`
  - `feed_max_page_size = 30`

## 结论

- `15` 已不仅是项目侧合同，也已经是当前生产默认运营基线。
- 首页窗口与 feed contract 仍保持 `30/30`，没有被误伤。
- `18` 继续只保留为 `near-publish boundary`。
