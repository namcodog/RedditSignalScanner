# Agent-Builder Signal Canary V1

日期：2026-04-08

## 目标

在不重开大范围 pack prompt 实验的前提下，只针对 `agent-builder` 当前最集中的两个失败项做一个最小 canary：

- `reddit_restatement`
- `why_now_not_actionable`

## canary 设计

### baseline

- `human_summary_tight_why_now_v1`

### candidate

- `agent_builder_signal_readout_v1`

策略不是重写大 prompt，而是加一层 deterministic readout：

- repo / lint / clickbait 场景：
  - 强调“具体错误清单”和“可复验发现”
- SQL / code-style 场景：
  - 强调“数据库相关代码重新拉回 ORM + 人审”
- hype / prompt-engineering / cost 场景：
  - 强调“提示词维护 + 持续运行成本”

## 结果

```json
[
  {
    "variant_id": "human_summary_tight_why_now_v1",
    "pass_rate": 0.0,
    "pass_count": 0,
    "fail_count": 3,
    "decision": "baseline"
  },
  {
    "variant_id": "agent_builder_signal_readout_v1",
    "pass_rate": 0.6667,
    "pass_count": 2,
    "fail_count": 1,
    "decision": "keep"
  }
]
```

## 失败分布

```json
{
  "pass_count": 2,
  "fail_count": 1,
  "top_failure_tags": [
    ["reddit_restatement", 1],
    ["no_judgment_gain", 1]
  ]
}
```

## 判断

`agent-builder` 已经不再只是 readiness 阶段。

当前可以给出更硬的结论：

- 供给修复有效
- 最小 canary 有明确提升
- `agent_builder_signal_readout_v1` 值得 promote 进生产链

## 下一步

`selection-signals` 和 `agent-builder` 都已经拿到 pack 级 keep 结果，V2 下一步应切换到：

- `breakdown V2`
