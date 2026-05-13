# Phase 669 - Tools Efficiency Supply Fix V3

## 发现了什么

- `tools-efficiency` 第二轮修完后，虽然能稳定产出 `3` 条 eval case，但 judge 仍然是 `0/3 pass`。
- 根因不是“还没 search-first”，而是对低 quota pack 来说：
  - 即使已经 `search-first`
  - 只要 spec 仍按 `category -> problem -> change`
  - 宽 query 还是会先把 quota 吃满
- 所以这轮最该修的不是再换 prompt，而是：
  - 更窄的社区池
  - 更窄的 query
  - 更合理的 bucket priority

## 是否需要修复

需要，而且这轮仍然属于供给修复，不是 pack prompt 实验。

## 精确修复方法

- `tools-efficiency` 社区池改成：
  - `ChatGPT`
  - `ClaudeAI`
  - `OpenAI`
  - `cursor`
- 删除更容易抓到 builder 经验帖和泛 AI 讨论的入口：
  - `automation`
  - `ClaudeCode`
  - `ai tool stack`
  - `prompt workflow`
  - `which ai tools are worth paying for`
- 保留以“工具切换/订阅取舍/上下文丢失”为中心的 query
- 在 `reddit_search_spec_builder.py` 里给 `tools-efficiency` 加了独立 bucket priority：
  - `problem -> change -> category`

### 测试

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_catalog.py \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py \
  backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`13 passed`

## 真实结果

- collect：
  - `ClaudeAI / tool switching fatigue`
  - `ChatGPT / copy paste context between tools`
  - `ClaudeAI / copy paste context between tools`
- eval：
  - `case_count = 2`
  - `generation_failure_count = 1`
- judge：
  - `pass = 0`
  - `fail = 2`
  - 高频失败标签：
    - `reddit_restatement`
    - `why_now_not_actionable`
    - `quote_not_used_well`

## 下一步系统性的计划是什么

1. 保留当前更窄的 `tools-efficiency` 供给配置
2. 不把它误判成“已经能做正式 pack 实验”
3. 下一步如果继续，只做一个很小的定向 canary：
   - 专打：
     - `reddit_restatement`
     - `why_now_not_actionable`
4. 不继续做大范围 pack prompt 实验

## 这次执行的价值是什么

这轮把 `tools-efficiency` 的状态说真话了：

- 之前是“抓到的东西就不对”
- 现在是“抓的方向开始对了，但写法还没被证明”

这比盲目继续换 prompt 更有价值，因为它避免我们把还没成熟的 pack 误推进成正式实验。
