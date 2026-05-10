# Phase 659 - Signal Judge Calibration V1

## 结果

`signal judge` 已经从文档推进成真实可跑的离线评审器，并完成了第一轮 calibration。

本轮产物：

- `reports/evals/signal_judge_calibration_labels_v1.jsonl`
- `reports/evals/signal_judge_calibration_v1.md`
- `reports/evals/signal_judge_prompt_v1.md`
- `reports/evals/signal_judge_calibration_predictions_v1.jsonl`
- `reports/evals/signal_judge_calibration_summary_v1.json`

## 核心结果

在 `8` 条人工校准样本上：

- `overall_match_rate = 1.0`
- `exact_tag_match_rate = 0.5`

也就是说：

- **整卡 pass/fail 已经完全对齐人工判断**
- **failure tags 还没有完全对齐，当前更适合当“整卡评委”，还不适合当“细粒度失败标签裁判”**

## 当前判断

这轮最重要的不是分数本身，而是边界终于清楚了：

1. judge 已经能稳定判断整卡值不值
2. judge 还会在细标签上过度补标签或偏向错误标签
3. 当前最稳的推进方式不是继续纠缠 tags，而是：
   - 先把 judge 用作整卡级 gate
   - 再做第二轮 tag calibration

## 已钉住的校准边界

- `why_now` 轻微模板味，不自动等于整卡 fail
- `reddit_restatement` 不能只看“有没有引用”，要看是否“引用成了主体”
- `no_judgment_gain` 是整卡级硬伤
- 弱证据样本可以 pass，但前提是输出收得住

## 下一步

下一步应直接做：

1. 用当前 judge 跑完整 `36` 条 signal eval set
2. 看整卡级 `pass/fail` 分布
3. 再决定：
   - 先进入 autoresearch loop
   - 还是先补第二轮 tag calibration
