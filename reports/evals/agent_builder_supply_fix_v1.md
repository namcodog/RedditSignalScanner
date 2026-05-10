# Agent-Builder Supply Fix V1

日期：2026-04-07

## 目标

把 `agent-builder` 从：

- `LocalLLaMA` 单社区 hype / 发布帖

推进到：

- 更像 agent 落地门槛、tool-calling 可靠性、上下文丢失的真实信号输入

## 本轮改动

### 1. 社区池收窄

从：

- `LocalLLaMA`
- `ChatGPTCoding`
- `ClaudeAI`
- `automation`
- `artificial`

改为：

- `ChatGPTCoding`
- `ClaudeAI`
- `OpenAI`
- `cursor`
- `automation`

### 2. query 重写

旧 query 偏泛：

- `llm`
- `agent`
- `workflow automation`
- `reasoning model`

新 query 偏落地门槛：

- `agent broke in production`
- `tool calling unreliable`
- `context loss in agent loop`
- `agent ignored tool result`
- `agent fails after multiple steps`
- `stopped using agent framework`
- `replaced agent stack`
- `cut agent steps`
- `moved from agent to workflow`
- `agent eval caught bug`
- `agent evaluation`
- `tool calling workflow`
- `agent observability`

### 3. 采集结构调整

- `agent-builder` 改成 `search-first`
- `agent-builder` 每个 spec 只允许贡献 `1` 条帖子

## 定向测试

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py -q
```

结果：`7 passed`

## 真实 collect 结果

```json
{
  "agent_builder_count": 3,
  "agent_builder": [
    {
      "community": "r/OpenAI",
      "title": "I scanned 10 popular vibe-coded repos with a deterministic linter. 4,513 findings across 2,062 files. Here's what AI agents keep getting wrong.",
      "matched_keywords": ["tool calling unreliable"]
    },
    {
      "community": "r/cursor",
      "title": "Cursor keeps generating SQL queries like this and it's making me nervous",
      "matched_keywords": ["tool calling unreliable"]
    },
    {
      "community": "r/automation",
      "title": "The bull** around AI agent capabilities on Reddit is getting out of hand",
      "matched_keywords": ["context loss in agent loop"]
    }
  ]
}
```

结论：

- 方向已经修对
- 不再由 `LocalLLaMA` 发布兴奋帖主导
- 现在抓到的是更像“落地门槛/可靠性”的输入

## readiness 复审

### 生成层

```json
{
  "case_count": 3,
  "generation_failure_count": 0
}
```

### judge 层

```json
{
  "pass_count": 0,
  "fail_count": 3,
  "top_failure_tags": [
    ["reddit_restatement", 3],
    ["why_now_not_actionable", 3],
    ["quote_not_used_well", 1]
  ]
}
```

## 最终判断

`agent-builder` 已经从“供给方向错了”推进到“供给方向对了，但写法还没过关”。

这意味着：

- 现在不该继续修社区池和 query
- 也不该直接开正式 pack 实验
- 下一步应该开一个很小的 `agent-builder` canary，只打：
  - `reddit_restatement`
  - `why_now_not_actionable`
