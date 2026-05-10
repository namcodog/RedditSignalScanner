# Phase 674 - Agent-Builder Supply Fixed, Prompt Still Held

## 本阶段结论

`agent-builder` 这条线已经从“供给方向错了”推进到“供给方向修对了”，但还没有推进到“可以开正式 pack prompt 实验”。

当前真实状态是：

- 输入供给：
  - 已从 `LocalLLaMA` 单社区发布兴奋帖，收窄为 `OpenAI / cursor / automation / ChatGPTCoding / ClaudeAI`
  - 已改成 `search-first`
  - 已限制每个 spec 只吃 `1` 条帖子
- readiness：
  - `case_count = 3`
  - `generation_failure_count = 0`
  - `judge pass = 0 / 3`

## 本阶段完成

1. `agent-builder` 社区池与 query 重写
2. `agent-builder` 改成 `search-first`
3. `agent-builder` candidate cap 改成 `1`
4. 测试口径从“保留 broad listing”翻到“优先 reliability signals”
5. 真实 collect + readiness 复审完成

## 关键验证

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py -q
```

结果：`7 passed`

## 产品判断

这轮最值钱的不是让 `agent-builder` 直接过关，而是把它从“抓错东西”纠正成“抓对东西但还没写好”。

这说明下一步已经很清楚：

- 不再继续修供给
- 也不直接开正式 pack 实验
- 先做一个很小的 `agent-builder` canary，只打：
  - `reddit_restatement`
  - `why_now_not_actionable`

## 下一步

1. 为 `agent-builder` 设计最小 canary 变体
2. 只验证：
   - 能不能压住 Reddit 转述腔
   - 能不能把 `why_now` 写成可用的信号读数
3. 根据 canary 结果决定：
   - 开正式 pack 实验
   - 或继续挂起
