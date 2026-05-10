# Phase 761 - 已发布语义刷新 CLI 结果锁定

时间：2026-04-11 08:00 CST

## 发现

- 旧版 `refresh_published_card_semantics.py` 的 `dry-run` 和 `--apply` 都会各自重新调一次刷新链路。
- 这会导致同一批卡在审核样本和正式写回之间发生轻微漂移，尤其是 LLM 字段改写后不完全一致。

## 修复

- 给 CLI 增加两条明确能力：
  - `--output-plan <file>`：把当前 dry-run 产出的精确写回内容落成 plan JSON。
  - `--apply-plan <file>`：只按 plan 里的 `refreshed_card` 写回，不再重新调用 LLM。
- `--apply-plan` 现在会禁止和 live selector 混用：
  - `--card-id`
  - `--lane`
  - `--card-type`
  - `--limit`
  - `--all`
  - `--output-plan`
- 新增脚本级测试，卡住两条关键边界：
  - dry-run 产出的 plan 必须包含完整 `refreshed_card`
  - apply-plan 写回时不能再读 published 全量，也不能再进刷新函数

## 验证

- `python -m py_compile backend/scripts/hotpost/refresh_published_card_semantics.py`
- `pytest backend/tests/scripts/hotpost/test_refresh_published_card_semantics.py -q --tb=short -p no:schemathesis`
- `pytest backend/tests/services/hotpost/test_published_card_semantic_refresh.py backend/tests/scripts/hotpost/test_refresh_published_card_semantics.py -q --tb=short -p no:schemathesis`

结果：

- 编译通过。
- 脚本级测试 `3 passed`。
- 相关回归 `7 passed`。
- 这一步只补 CLI 合同，没有改动已发布数据。

## 下一步

- 后续刷新已发布卡时统一改成两段式：
  1. `dry-run + --output-plan`
  2. 人工确认后 `--apply-plan`
- 这样可以把“看到的样本”和“真正写回的内容”锁成同一份结果。
