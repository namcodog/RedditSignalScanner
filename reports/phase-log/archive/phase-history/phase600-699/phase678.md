# Phase 678 - breakdown eval set v1 落地

## 发现了什么

`breakdown skill optimization` 的第一块地基已经从合同变成真实产物：

- 新增 `breakdown_eval_set_builder`
- 新增导出脚本 `build_breakdown_eval_set_v1.py`
- 已成功导出 `breakdown eval set v1`

这一步没有去碰：

- `suggestion` 门槛
- `materialize` 主链
- `publish` 闸门

范围保持在 `write / breakdown` 的内容质量评估层。

## 是否需要修复

这一步本身不需要补修。

当前结果已经足够进入下一环：

- human review
- failure taxonomy
- breakdown judge v1

## 精确修复方法

本阶段新增：

- `backend/app/services/hotpost/breakdown_eval_set_builder.py`
- `backend/scripts/evals/build_breakdown_eval_set_v1.py`
- `backend/tests/services/hotpost/test_breakdown_eval_set_builder.py`

验证：

```bash
SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_breakdown_eval_set_builder.py -q
python backend/scripts/evals/build_breakdown_eval_set_v1.py
```

结果：

- `2 passed`
- 导出成功：
  - `reports/evals/breakdown_eval_set_v1.jsonl`
  - `reports/evals/breakdown_eval_labels_v1.jsonl`
  - `reports/evals/breakdown_eval_synthetic_plan_v1.jsonl`
  - `reports/evals/breakdown_eval_generation_failures_v1.jsonl`
  - `reports/evals/breakdown_eval_manifest_v1.json`

manifest：

- `real_count = 18`
- `synthetic_plan_count = 6`
- `generation_failure_count = 0`
- `topic_pack_counts = {"agent-builder": 1, "selection-signals": 1, "unknown": 16}`

## 下一步系统性的计划是什么

下一步直接进入：

1. `breakdown review packet v1`
2. `breakdown failure taxonomy v1`
3. `breakdown judge v1`

## 这次执行的价值是什么

这次的价值不是“多出几张拆解卡”，而是把拆解优化从抽象方向推进成了一个真正可执行的评估底座。

从现在开始，`breakdown skill optimization` 不再靠感觉讨论，而是可以像之前的 `signal skill` 一样，进入：

`eval set -> human review -> taxonomy -> judge -> canary`
