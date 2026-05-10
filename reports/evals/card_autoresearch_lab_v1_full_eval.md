# card-autoresearch-lab v1 full eval

## 范围
- 对象：`signal_eval_set_v1.jsonl`
- 样本数：`31`
- 变体：
  - `human_summary_tight_why_now_v1`
  - `judgment_forward_summary_v2`
  - `judgment_forward_summary_strict_v2`
- 执行方式：
  - `batch-size = 4`
  - `concurrency = 4`
  - 分批跑完整 eval

## 结果

| variant | pass | fail | pass_rate | decision |
|---|---:|---:|---:|---|
| `human_summary_tight_why_now_v1` | 11 | 20 | 0.3548 | baseline |
| `judgment_forward_summary_v2` | 11 | 20 | 0.3548 | discard |
| `judgment_forward_summary_strict_v2` | 10 | 21 | 0.3226 | discard |

## 结论
- 当前 `card-autoresearch-lab v1` 已经能稳定跑完整 `signal eval`，不再停留在 smoke。
- 这轮没有跑出新的 keep。
- `judgment_forward_summary_v2` 虽然和 baseline 打平，但没有超过 baseline，不值得 promote。
- `judgment_forward_summary_strict_v2` 明显更差，应继续 discard。

## 关键信号

### baseline 仍然最稳
- `human_summary_tight_why_now_v1` 仍然是当前 signal 的最优默认写法。

### “更早下判断”没有自动带来更好结果
- `judgment_forward_summary_v2`
  - `pass_rate` 与 baseline 持平
  - 但 `reddit_restatement / no_judgment_gain / why_now_not_actionable` 仍高
- `judgment_forward_summary_strict_v2`
  - 进一步放大了 `reddit_restatement`
  - 还带来了更多 `quote_not_used_well`

### 当前最差的 scope 还没被 prompt 一把救回来
- baseline fail 仍主要集中在：
  - `ai-automation`
  - `business-growth-ops`
- 说明这轮问题不是“少一个更猛的总 prompt”，而是更细的 pack 问题还在。

## 工程判断
- `card-autoresearch-lab v1` 当前已经有价值：
  - 能离线、受控、分批跑完完整 eval
  - 能在现有 judge 上稳定产出 keep/discard
- 但这轮也证明：
  - 不能指望一个全局更猛的 prompt，直接把 signal 整体拉起来
  - 下一步更值的是：
    - 扩到 `polish` 层实验
    - 或按 pack 做更窄的变体实验

## 本轮补的关键稳定性
- `run_card_autoresearch_lab_v1.py` 已支持：
  - `--batch-size`
  - `--concurrency`
  - 分批汇总
- `card_autoresearch_lab.py` 已支持：
  - 单 case 失败容错
  - `lab_runtime_error` 落盘
  - 整轮实验不中断
