# Phase 663 - Signal Quality Gate Effect Check

## 结果

`signal input quality gate` 接入 signal 生成主链后，已经完成了一轮真正的整体验证：

1. 重建 `signal eval set`
2. 重跑 `signal judge`
3. 对比接闸前后的 fail 分布

新增产物：

- `reports/evals/signal_quality_gate_effect_v1.md`
- 更新后的：
  - `reports/evals/signal_eval_set_v1.jsonl`
  - `reports/evals/signal_eval_manifest_v1.json`
  - `reports/evals/signal_judge_full_eval_predictions_v1.jsonl`
  - `reports/evals/signal_judge_full_eval_summary_v1.json`

## 接闸前后对比

### 接闸前

- `sample_count = 36`
- `pass = 14`
- `fail = 22`
- `pass_rate = 38.89%`

### 接闸后

- `sample_count = 31`
- `pass = 11`
- `fail = 20`
- `pass_rate = 35.48%`

## 当前判断

如果只看总 pass rate，会误判。

真正该看的有两条：

### 1. 质量闸门确实挡掉了最脏输入

- `real_count: 36 -> 31`
- `generation_failure_count = 8`
- `quote_not_used_well: 6 -> 3`

也就是说：

**bot / 公版废话 / 单帖弱证据 这类垃圾输入，确实被挡掉了。**

### 2. 但主问题仍然在新生成链

- `reddit_restatement` 仍然是 `18`
- `candidate_generated` 当前仍然是 `0 pass / 15 fail`

这说明：

**signal input quality gate 是必要层，但不是充分层。**

它能去垃圾，但不能自动把剩下的卡写好。

## 当前结论

这轮验证把角色边界彻底讲清楚了：

- `signal input quality gate`
  - 负责挡最脏输入
- `signal skill optimization`
  - 负责把“值得写的输入”写成真正过关的卡

当前这两条都必须保留，不能再拿一个去替代另一个。

## 下一步

下一步不该回头怀疑闸门。

应直接做：

1. 保留 `signal input quality gate`
2. 在新的更干净输入盘子上，继续第二轮 signal skill 实验
3. 重点继续打：
   - `reddit_restatement`
   - `no_judgment_gain`
4. 优先 pack：
   - `business-growth-ops / paid-economics`
   - `ai-automation / tools-efficiency`
