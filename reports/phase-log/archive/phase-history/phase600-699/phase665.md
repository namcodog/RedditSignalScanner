# Phase 665 - Pack Readiness Audit

## 发现了什么

- 原计划进入 pack 定向 `signal skill` 实验：
  - `business-growth-ops / paid-economics`
  - `ai-automation / tools-efficiency`
- 但实际 audit 后发现，这两个 pack 当前都**不具备进入 skill 实验的条件**

### 实际结果

- `paid-economics`
  - candidate：`3`
  - 通过 `signal input quality gate`：`0`
  - 被挡：`3`
- `tools-efficiency`
  - candidate：`3`
  - 通过 `signal input quality gate`：`0`
  - 被挡：`3`

拦截原因高度集中：

- `single_thread_weak_evidence`
- `single_community_weak_evidence`
- 个别样本还有：
  - `no_substantive_quotes`

## 是否需要修复

需要，但修的不是 prompt。

这轮已经证明：

- 这两个 pack 的主问题不是“写法差”
- 而是“输入供给不配生成 signal 卡”

所以当前不该继续做 pack 定向 prompt 优化。

## 精确修复方法

### 本轮实现

- 新增 pack 定向 eval builder：
  - `backend/app/services/hotpost/signal_pack_eval_builder.py`
- 新增测试：
  - `backend/tests/services/hotpost/test_signal_pack_eval_builder.py`

### 验证

```bash
SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_signal_pack_eval_builder.py backend/tests/services/hotpost/test_signal_skill_experiment.py -q
```

- 测试结果：`6 passed`

### 审计产物

- `reports/evals/signal_pack_readiness_audit_v1.md`

## 下一步系统性的计划是什么

1. 暂停这两个 pack 的定向 `signal skill` 实验
2. 先回到供给侧修复：
   - query
   - subreddit 选择
   - collect 信号结构
3. 等这两个 pack 能稳定产出通过 `signal input quality gate` 的候选，再重新进入定向 skill 实验

## 这次执行的价值是什么

这轮不是“没做成实验”，而是避免了在错误层级上浪费时间。

现在边界已经很清楚：

- `signal skill` 优化只对“值得写的样本”有意义
- `paid-economics` 和 `tools-efficiency` 当前还没到这一步

所以主线必须从“改写法”切回“修输入供给”。
