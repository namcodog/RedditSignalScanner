# Phase 675 - Agent-Builder Promoted, V2 Ready For Breakdown

## 本阶段结论

`agent-builder` 已完成：

1. 输入供给修复
2. readiness 复审
3. 最小 canary
4. 生产 promote

当前结果：

- `human_summary_tight_why_now_v1 = 0/3 pass`
- `agent_builder_signal_readout_v1 = 2/3 pass`
- 结论：`keep`

因此，V2 主线里原本锁定的两条 pack：

- `selection-signals`
- `agent-builder`

都已经拿到 pack 级 keep 结果。

## 本阶段完成

### 1. agent-builder 供给修复

- 社区池从 `LocalLLaMA` 兴奋帖主导，切到：
  - `OpenAI`
  - `cursor`
  - `automation`
  - `ChatGPTCoding`
  - `ClaudeAI`
- 改成 `search-first`
- 每个 spec 只允许贡献 `1` 条帖子

### 2. agent-builder 最小 canary

只打两个问题：

- `reddit_restatement`
- `why_now_not_actionable`

通过 deterministic readout，把三类样本压成更贴业务边界的 signal：

- repo/lint/检查链
- SQL/ORM/人工把关
- prompt engineering / 持续成本

### 3. 生产接线

`agent_builder_signal_readout_v1` 已接进 signal 生成主链。

## 关键验证

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_agent_builder_signal_overrides.py \
  backend/tests/services/hotpost/test_card_content_generator.py \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py -q
```

结果：`23 passed`

## 当前稳定资产

- 全局 signal 基线：
  - `human_summary_tight_why_now_v1`
- pack 专用写法：
  - `paid_econ_signal_readout_v2`
  - `selection_signal_readout_v1`
  - `agent_builder_signal_readout_v1`
- `signal judge`
- `signal input quality gate`

## 下一步

V2 不再继续扩 signal pack。

下一步正式切到：

- `breakdown skill V2`

原因：

- `selection-signals` 已成熟
- `agent-builder` 已成熟
- 两条线都天然适合作为 breakdown 的主战场
