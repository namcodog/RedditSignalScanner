# Phase 680 - breakdown judge calibration v2 完成

## 发现了什么

这轮推进的重点不是再补结构，而是把创始人的 18 条拆解卡人判，真正拿来校准 `breakdown judge`。

结果很清楚：

- `breakdown judge v1`
  - `overall_match_rate = 83.33%`
  - `exact_tag_match_rate = 77.78%`
- `breakdown judge v2`
  - `overall_match_rate = 88.89%`
  - `exact_tag_match_rate = 77.78%`

这说明 `v2` 已经明显比 `v1` 更贴近人工判断。

但这轮也把一个更重要的边界打出来了：

**单卡 judge 和卡组去重不是一回事。**

仍然没对齐的两张：

- `breakdown-eval-published-clue-roadmap-lightweight-alignment`
- `breakdown-eval-published-clue-sales-followup-slip`

都不是 thesis 完全错误，而是：

- 放在整组拆解里看，和相邻卡判断高度重叠
- 卡本身看着顺，但新增判断已经不够

也就是说：

- `breakdown judge v2` 已经够当**单卡 gate**
- 但“卡组里值不值得留下这张卡”要单独做 `overlap / dedupe audit`

## 是否需要修复

需要，但不是继续狂调 `judge prompt`。

当前更合理的做法是：

- 保留 `breakdown judge v2` 做单卡 gate
- 下一步单独补一层：
  - `breakdown overlap / dedupe audit`

## 精确修复方法

本阶段新增：

- `reports/evals/breakdown_judge_calibration_labels_v1.jsonl`
- `reports/evals/breakdown_judge_calibration_v1.md`
- `reports/evals/breakdown_judge_prompt_v2.md`
- `backend/scripts/evals/run_breakdown_judge_calibration_v1.py`
- `backend/scripts/evals/run_breakdown_judge_calibration_v2.py`
- `backend/scripts/evals/run_breakdown_judge_full_eval_v2.py`

本阶段更新：

- `reports/evals/breakdown_failure_taxonomy_v1.md`
  - 补了代表样本
  - 明确 `weak_thesis / stitched_not_coherent / reporty_title` 的边界
- `backend/app/services/hotpost/signal_judge_runner.py`
  - judge 返回里偶发夹带非 JSON 时，先抽出 JSON object 再解析，避免评测 runner 被脏返回打断

验证：

```bash
python backend/scripts/evals/run_breakdown_judge_calibration_v1.py
python backend/scripts/evals/run_breakdown_judge_calibration_v2.py
python backend/scripts/evals/run_breakdown_judge_full_eval_v2.py
```

结果：

- calibration v1:
  - `15 / 18 overall match`
- calibration v2:
  - `16 / 18 overall match`
- full eval v2:
  - `sample_count = 18`
  - `pass_count = 16`
  - `fail_count = 2`

当前 top failure tags：

- `weak_thesis`
- `quote_pack_not_supporting_claim`
- `stitched_not_coherent`

## 下一步系统性的计划是什么

下一步不再继续扩 judge 范围，而是按顺序做两件事：

1. 跑 `breakdown canary`
2. 单独补 `breakdown overlap / dedupe audit`

## 这次执行的价值是什么

这轮最值钱的不是“对齐率提高了 5 个点”，而是把拆解线里的两个判断层次彻底分开了：

- 单卡是否成立：`breakdown judge v2`
- 卡组里是否冗余：`overlap / dedupe audit`

这会让后面的拆解优化不再混成一锅。
