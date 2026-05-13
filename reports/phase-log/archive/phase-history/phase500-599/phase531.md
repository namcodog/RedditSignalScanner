# Phase 531 - Hotpost 召回精度第一刀落地

## 背景

- Phase 530 已把 Hotpost 当前主问题收窄为：
  - `Source Quality / Retrieval Precision`
- 当前不继续碰大架构，也不继续调 prompt。
- 目标是用轻量、配置驱动的方式，把明显错误的社区和假关键词命中挡在 evidence pack 之前。

## 本轮改动

### 1. 新增轻量 retrieval precision 模块

- 新增 [backend/app/services/hotpost/retrieval_precision.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/retrieval_precision.py)
- 体量控制在 `185` 行
- 只做三件事：
  - 识别 `trusted / unknown / suspicious` 来源
  - 给候选证据打 retrieval precision score
  - 对明显错误来源做硬阻断

### 2. Hotpost quality 配置新增 retrieval_precision

- 更新 [backend/config/hotpost_quality.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_quality.yaml)
- 新增配置项：
  - `trusted_subreddit_terms`
  - `suspicious_subreddit_terms`
  - `suspicious_title_terms`
  - `suspicious_body_terms`
  - `generic_query_terms`
  - `trusted_source_boost`
  - `unknown_source_penalty`
  - `required_focus_hits_for_opportunity`
  - `suspicious_source_block`

### 3. 接入 evidence collection 主链

- 更新 [backend/app/services/hotpost/evidence_collection_workflow.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/evidence_collection_workflow.py)
- 当前行为：
  - `opportunity` 模式下，明显作业互助/广告型社区直接挡掉
  - `trusted` 社区加权
  - `unknown` 社区降权
  - `why_relevant` 改写成更贴近“为什么这条证据该进来”的说明

### 4. 先写测试再落实现

- 新增 [backend/tests/services/hotpost/test_hotpost_retrieval_precision.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_hotpost_retrieval_precision.py)
- 额外更新：
  - [backend/tests/services/hotpost/test_evidence_collection_workflow.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_evidence_collection_workflow.py)
- 覆盖重点：
  - suspicious source 被挡掉
  - trusted shopify/ecommerce 语境被提升
  - `opportunity` 模式下错误来源不会进 top posts

## 验证

- 运行：
  - `pytest backend/tests/services/hotpost/test_hotpost_retrieval_precision.py backend/tests/services/hotpost/test_evidence_collection_workflow.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
- 结果：
  - `17 passed`

## 结论

### 1. 发现了什么？

- Hotpost 当前的主问题确实是算法层，不是架构层。
- 而且第一个该修的算法点，不是输出 wording，而是召回精度。

### 2. 是否需要继续修复？

- 需要。
- 这轮只完成了 `Source Quality / Retrieval Precision` 的第一刀。

### 3. 下一步系统性计划

- 进入下一刀：
  - `query planner semantic constraints`
- 重点补：
  - `positive_intent_terms`
  - `forbidden_context_terms`
  - `domain_terms`
- 然后再做最小 live 复验，不扩大 Reddit 调用。

### 4. 这次执行的价值

- 让 Hotpost 开始在“料进模型之前”就做第一层真伪筛选。
- 这比后面再让 report 层擦屁股更轻，也更稳。
- 同时守住了约束：
  - 不重工程化
  - 不增加兜底假结果
  - 不新增 live 调用去撞 Reddit API
