# Phase 532 - Hotpost Query Planner 语义约束落地

## 背景

- Phase 531 已完成 `source quality / retrieval precision` 第一刀。
- 下一步固定顺序是：
  1. `query planner semantic constraints`
  2. 最小 live 复验
- 目标不是继续扩架构，而是让 planner 产出的语义约束，真正进入召回层。

## 本轮改动

### 1. Query planner 补语义输出

- 更新 [backend/app/services/hotpost/query_planner.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/query_planner.py)
- 当前新增输出：
  - `positive_intent_terms`
  - `forbidden_context_terms`
  - `domain_terms`
- 语义输出来源仍然是配置驱动，不写死在代码里。

### 2. planner 配置补齐

- 更新 [backend/config/hotpost_quality.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_quality.yaml)
- `query_planner` 新增：
  - `positive_intent_terms`
  - `forbidden_context_terms`
  - `domain_terms`

### 3. 召回层开始吃 planner 语义约束

- 更新 [backend/app/services/hotpost/retrieval_precision.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/retrieval_precision.py)
- 更新 [backend/app/services/hotpost/evidence_collection_workflow.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/evidence_collection_workflow.py)
- 当前行为：
  - 命中 `positive_intent_terms` 会加权
  - 命中 `domain_terms` 会加权
  - 命中 `forbidden_context_terms` 会直接降权，并在 `opportunity` 等模式下阻止继续放行

### 4. Debug 合同补齐

- 更新 [backend/app/services/hotpost/response_bundle.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/response_bundle.py)
- 更新 [backend/app/schemas/hotpost.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/schemas/hotpost.py)
- 现在 `debug_info` 能直接看到：
  - `positive_intent_terms`
  - `forbidden_context_terms`
  - `domain_terms`

## 验证

- 运行：
  - `pytest backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_hotpost_retrieval_precision.py backend/tests/services/hotpost/test_evidence_collection_workflow.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
- 结果：
  - `21 passed`

## 结论

### 1. 发现了什么？

- Hotpost 这条线现在已经不是“planner 产出一些词但没人用”。
- planner 的语义约束已经真正进入 evidence collection 主链。

### 2. 是否需要继续修复？

- 需要。
- 但当前下一步不该继续留在单测层，而该做最小 live 复验。

### 3. 下一步系统性计划

- 只跑最小 live：
  - 1 条冷 `opportunity`
  - 优先看错误社区是否继续混入
  - 不扩大 Reddit 调用

### 4. 这次执行的价值

- 把“query planner 有语义”这件事从概念变成了运行时能力。
- 这轮之后，Hotpost 在召回层已经同时具备：
  - source quality
  - retrieval precision
  - semantic constraints
- 也继续守住了边界：
  - 核心文件单文件不超过 300 行
  - 不做重工程化
  - 不增加假兜底
