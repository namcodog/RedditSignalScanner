# Phase 664 - Signal Skill Experiment V2

## 发现了什么

- 第二轮 `signal skill` 实验已经跑完，目标不是继续“人话化”，而是验证更强的“判断前置”写法能不能打掉：
  - `reddit_restatement`
  - `no_judgment_gain`
- 当前基线采用上一轮 keep 版本：`human_summary_tight_why_now_v1`
- 第二轮两个新变体都没有赢过基线：
  - `human_summary_tight_why_now_v1`：`13/31 pass`，`41.94%`
  - `judgment_forward_summary_v2`：`7/31 pass`，`22.58%`
  - `judgment_forward_summary_strict_v2`：`10/31 pass`，`32.26%`

## 是否需要修复

需要，但不是继续做“一刀切总 prompt”。

这一轮已经证明：

- 全局把 `summary_line` 强行改成“先给判断句”
- 并不能稳定提升 signal 卡质量
- 反而会让一部分卡更像空判断或假判断

所以主方向要收窄成：

- 保留当前最优基线
- 改成 pack 定向优化

## 精确修复方法

### 本轮实现

- 新增变体策略模块：
  - `backend/app/services/hotpost/signal_skill_variant_policy.py`
- 扩展实验变体：
  - `judgment_forward_summary_v2`
  - `judgment_forward_summary_strict_v2`
- 新增第二轮实验 runner：
  - `backend/scripts/evals/run_signal_skill_experiment_v2.py`
- 补充实验测试：
  - `backend/tests/services/hotpost/test_signal_skill_experiment.py`

### 验证

```bash
SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_signal_skill_experiment.py backend/tests/services/hotpost/test_signal_eval_set_builder.py -q
python backend/scripts/evals/run_signal_skill_experiment_v2.py
```

- 测试结果：`7 passed`
- 第二轮实验结论已写入：
  - `reports/evals/signal_skill_experiment_v2.md`
  - `reports/evals/signal_skill_experiment_keep_discard_v2.json`

## 下一步系统性的计划是什么

1. 不继续做全局 `summary_line` 判断前置实验
2. 保留 `human_summary_tight_why_now_v1` 作为当前 signal 基线
3. 下一轮改成 pack 定向实验：
   - `business-growth-ops / paid-economics`
   - `ai-automation / tools-efficiency`
4. 继续用当前 judge 做 keep/discard，不直接 promote 到生产链

## 这次执行的价值是什么

这轮实验把一个很关键的边界打实了：

- `signal input quality gate` 负责去掉不该写的垃圾输入
- `signal skill` 不能再靠一个全局猛 prompt 解决所有主题

也就是说，系统现在已经从“乱调 prompt”推进到“知道该在哪一层、按什么粒度优化”。
