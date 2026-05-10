# Phase 667 - Paid Economics Pack Skill Experiment

## 发现了什么

- 在完成第一轮供给修复后，`business-growth-ops / paid-economics` 已经从：
  - `0/3` 全部被 gate 挡掉
  推进到：
  - `2` 条可写样本
- 但进入 pack 定向 `signal skill` 实验后，结果仍然是：
  - `0 pass / 2 fail`

### 变体结果

- `human_summary_tight_why_now_v1`
  - `0/2 pass`
- `paid_econ_decision_v1`
  - `0/2 pass`
- `paid_econ_decision_strict_v1`
  - `0/2 pass`

## 是否需要修复

需要，但不是继续叠 pack prompt。

这轮已经说明：

- `paid-economics` 不再是“完全没法写”
- 但当前样本仍然不够稳，写法改动救不回来

## 精确修复方法

### 本轮实现

- 新增 `paid-economics` pack 变体：
  - `paid_econ_decision_v1`
  - `paid_econ_decision_strict_v1`
- 新增定向 runner：
  - `backend/scripts/evals/run_paid_econ_signal_skill_experiment_v1.py`
- 补测试：
  - `backend/tests/services/hotpost/test_signal_skill_experiment.py`

### 验证

```bash
SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_signal_skill_experiment.py backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
python backend/scripts/evals/run_paid_econ_signal_skill_experiment_v1.py
```

- 测试结果：`7 passed`
- 实验结论已写入：
  - `reports/evals/paid_econ_signal_skill_experiment_v1.md`

## 下一步系统性的计划是什么

1. 暂停 `paid-economics` 的继续 prompt 实验
2. 继续修它的供给，让它从：
   - 单帖 incident / 吐槽
   变成：
   - 更像多角度、多帖的投放经济信号
3. `tools-efficiency` 继续停在供给修复线
4. 等这两个 pack 都能稳定产出过 gate 且至少部分过 judge 的样本，再重新开 pack skill 实验

## 这次执行的价值是什么

这轮把边界又往前推了一步：

- 不是所有“刚过 gate 的样本”都适合立即进入 pack skill 优化
- `paid-economics` 现在已经从“根本不配写”推进到“配写但不配优化”

这一步避免了后面继续在不成熟样本上浪费 prompt 迭代。
