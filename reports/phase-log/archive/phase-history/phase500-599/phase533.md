# Phase 533 - Hotpost 语义约束 live 复验

## 背景

- Phase 532 已把 `query planner semantic constraints` 接到召回主链。
- 这轮不继续扩代码面，重点是用最小 live 验证：
  - 错误社区有没有被压下去
  - 新算法会不会收得过紧

## live 复验

### Query

- `shopify chargeback response automation tool`
- mode=`opportunity`
- `query_id=a7705f83-6c7b-48eb-8110-834bf3006061`

### 结果

- `status=degraded`
- `evidence_count=2`
- `confidence=low`
- `communities=['shopify']`
- `quality_contract_gaps=[]`
- `degraded_reasons=['low_confidence']`

### 关键观测

- 错误社区已经明显收下去了：
  - 没再混进 `PiggyMyCrypto`
  - 没再混进 `SampleSize`
- 但结果也变保守了：
  - 只剩 `r/shopify`
  - 证据数掉到 `2`
- 这说明：
  - `source quality + semantic constraints` 已经开始生效
  - 但当前算法还缺“严格领域锚点”这一层

## 根因更新

- 现在的主问题已经不是“错误社区乱入”。
- 新主问题是：
  - **在正确社区里，如何避免被泛 Shopify 自动化帖子带偏**
- 当前 query 是：
  - `shopify + chargeback + response + automation + tool`
- 但 live 结果里仍然出现：
  - 库存同步
  - listing automation
- 说明现在的召回层还没有强制要求：
  - 至少命中一个“严格问题域锚点”
  - 比如这条 query 里的 `chargeback / response`

## 结论

### 1. 发现了什么？

- 这轮算法已经把“脏社区问题”明显压下去了。
- 但又暴露出新的精度问题：
  - 结果会落到“对社区，但不对问题”的帖子上。

### 2. 是否需要继续修复？

- 需要。
- 但下一刀不该回到 source quality，而该做：
  - `strict domain anchors`

### 3. 下一步系统性计划

- 下一刀只做轻量算法：
  - 从 query 里提炼严格领域锚点
  - `opportunity` 召回时，至少命中一个严格锚点才允许高优先进入 evidence pack
- 然后再跑 1 条最小 live 复验，不扩大 Reddit 调用。

### 4. 这次执行的价值

- 这轮已经把 Hotpost 当前算法问题从“大而模糊”继续收窄成一个很具体的小口子：
  - 不是社区脏
  - 是缺少“问题域锚点”
