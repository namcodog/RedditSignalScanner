# Phase 529 - Hotpost 冷 opportunity live 校准

## 背景

- Phase 528 已把 `top_quotes` 和 `market_opportunity` 的轻量算法层补上
- 本轮只跑 1 条新的冷 `opportunity` query，验证这两层在真实 live 下是否已经站住

## 本轮执行

### 1. 仅跑 1 条冷 query

- query: `shopify chargeback prevention software`
- mode: `opportunity`
- query_id: `3b70f245-26a1-461b-bbdb-dc8d4a071b0f`

### 2. 结果

- `status = completed`
- `from_cache = false`
- `report_source = llm`
- `final_report_layer = reasoning`
- `confidence = medium`
- `evidence_count = 10`

### 3. 关键观察

- 正向：
  - `top_quotes` 已不再混入 `Interested / same here` 这类低价值短回复
  - `market_opportunity` 已能补出：
    - `target_user`
    - `pricing_hint`
    - `gtm_channel`
    - `recommendation`
- 反向：
  - 结果仍然不够硬
  - 主要原因不是输出层又坏了，而是证据召回仍然偏脏：
    - `eductionalpartner`
    - `mathshelper`
    - `OnlineHESIExam`
  - `top_quotes` 虽然变成了“像样的句子”，但依然来自错误语境
  - `market_opportunity` 虽然字段补齐了，但因为输入证据不对，只能给出保守结论

### 4. timing

- `scout_ms = 4238`
- `comments_ms = 6521`
- `evidence_collection_ms = 10842`
- `summary_ms = 8002`
- `fast_report_ms = 17181`
- `reasoning_report_ms = 10860`
- `total_workflow_ms = 46924`

## 结论

### 1. 发现了什么？

- Phase 528 的算法没有白做：
  - `top_quotes` 过滤方向是对的
  - `market_opportunity` 投影方向也是对的
- 但当前 Hotpost 还没收口，剩下的主问题已经进一步收窄成：
  - **召回精度算法**

### 2. 是否需要继续修复？

- 需要
- 但下一刀不该去抠 prompt，也不该再扩架构
- 应该回到轻量算法层，继续收：
  - source quality / spam 社区过滤
  - direct-hit 精度
  - subreddit 信任度

### 3. 下一步系统性计划

1. 给 `opportunity` 增加轻量 source quality 过滤
2. 让明显垃圾社区在进入 evidence pack 前被压掉
3. 保持“配置驱动、轻量、不过度工程化”

### 4. 这次执行的价值

- 这次 live 把问题从“结果还不够硬”进一步缩小到：
  - **不是 quote 算法先坏**
  - **不是 market 字段先坏**
  - **而是召回证据还不够准**
