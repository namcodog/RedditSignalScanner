# Phase 660 - Signal Skill Experiment V1

## 结果

`signal judge` 已经跑完完整 `36` 条 `signal eval set`，并基于这个 judge 启动了第一轮半自动 signal skill 实验。

本轮新增产物：

- `reports/evals/signal_judge_full_eval_predictions_v1.jsonl`
- `reports/evals/signal_judge_full_eval_summary_v1.json`
- `reports/evals/signal_skill_experiment_v1.md`
- `reports/evals/signal_skill_experiment_keep_discard_v1.json`
- `reports/evals/signal_skill_experiment_*_outputs_v1.jsonl`
- `reports/evals/signal_skill_experiment_*_judge_v1.jsonl`
- `reports/evals/signal_skill_experiment_*_summary_v1.json`

## judge 全量结果

完整 `36` 条 signal eval set 的 judge 结果：

- `pass = 14`
- `fail = 22`
- `pass_rate = 38.89%`

最关键的发现：

- `published_validate`: `12 pass / 0 fail`
- `candidate_generated`: `2 pass / 22 fail`

这说明当前最大问题已经被钉死：

**历史已发布卡基本稳，真正差的是“新生成链”的 signal skill。**

高频失败标签：

1. `reddit_restatement = 18`
2. `no_judgment_gain = 12`
3. `why_now_not_actionable = 10`
4. `quote_not_used_well = 6`

## 第一轮实验

本轮只做离线半自动实验，不动生产链。

比较了 3 个变体：

1. `baseline_v1`
2. `human_summary_v1`
3. `human_summary_tight_why_now_v1`

结果：

- `baseline_v1`: `pass_rate = 13.89%`
- `human_summary_v1`: `pass_rate = 11.11%`
- `human_summary_tight_why_now_v1`: `pass_rate = 27.78%`

## 当前判断

这轮实验已经说明两件事：

1. **单改 summary 没用**
   - 只是把句子写得更像人话，不足以让卡真正完成判断前移
2. **有效的是“summary 人话化 + why_now 收紧”组合**
   - `why_now_not_actionable` 从 `13` 降到 `6`
   - `reddit_restatement` 从 `28` 降到 `21`

但也要说真话：

- `human_summary_tight_why_now_v1` 只是第一轮 keep
- 还没到能直接 promote 到生产链的程度
- 因为 `reddit_restatement` 和 `no_judgment_gain` 仍然是头号失败项

## 下一步

下一步应直接做：

1. 把 `human_summary_tight_why_now_v1` 做成 canary 候选
2. 第二轮实验继续只打：
   - `reddit_restatement`
   - `no_judgment_gain`
3. 优先盯最差 topic pack：
   - `business-growth-ops / paid-economics`
   - `ai-automation / tools-efficiency`
