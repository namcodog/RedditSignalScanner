# card-autoresearch-lab v2 full eval

## 范围
- 对象：`signal_eval_set_v1.jsonl`
- 样本数：`31`
- 固定底座：
  - prompt 层固定为当前最优 `human_summary_tight_why_now_v1`
- 变体：
  - `baseline_polish_v1`
  - `clean_summary_polish_v1`
  - `clean_summary_tight_why_now_polish_v1`
- 执行方式：
  - `batch-size = 4`
  - `concurrency = 4`
  - 分批跑完整 eval

## 结果

| variant | pass | fail | pass_rate | decision |
|---|---:|---:|---:|---|
| `baseline_polish_v1` | 13 | 18 | 0.4194 | baseline |
| `clean_summary_polish_v1` | 15 | 16 | 0.4839 | keep |
| `clean_summary_tight_why_now_polish_v1` | 8 | 23 | 0.2581 | discard |

## 结论
- `polish` 层实验跑出了新的 keep：
  - `clean_summary_polish_v1`
- 这说明当前更值的不是继续赌新的全局 prompt，而是先把最后一公里表达收紧。
- `clean_summary_tight_why_now_polish_v1` 明显更差，说明 `why_now` 这层不能靠一条更短的统一句子粗暴替换。

## 关键信号

### 只清 summary，真的有效
- `clean_summary_polish_v1`
  - `pass_rate: 0.4194 -> 0.4839`
  - `reddit_restatement: 17 -> 14`
  - `why_now_not_actionable: 7 -> 5`
- 说明 summary 去转述腔，已经能直接改善 judge 结果。

### 连 why_now 一起硬收，反而会写坏
- `clean_summary_tight_why_now_polish_v1`
  - `pass_rate: 0.2581`
  - `reddit_restatement / no_judgment_gain / why_now_not_actionable` 全面恶化
- 说明这层不能靠统一短句一刀切。

### 哪些 scope 受益更明显
- `clean_summary_polish_v1` 的提升主要出现在：
  - `ecommerce-sellers`
  - `business-growth-ops`
- `ai-automation` 仍然偏弱，说明 AI 线的问题不只是 summary 腔调。

## 工程判断
- `card-autoresearch-lab v2` 已证明：
  - 可以把 `polish` 层也纳入离线 keep/discard 闭环
  - 而且这层比继续找新的总 prompt 更容易出效果
- 当前最合理的 promote 边界是：
  - **只 promote `clean_summary_polish_v1`**
  - **不 promote `clean_summary_tight_why_now_polish_v1`**

## 建议动作
1. 把 `clean_summary_polish_v1` promote 到生产生成链的 polish 层。
2. 暂不动 `why_now` 的统一 polish。
3. 如果继续做 v3，优先考虑：
   - 标题去报告腔
   - pack 级 polish，而不是再做统一 `why_now` 改写
