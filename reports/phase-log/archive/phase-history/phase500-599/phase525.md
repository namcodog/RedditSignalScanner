# Phase 525 - DB 真相源重构第二刀：reconciliation 写入层落地

## 时间
- 2026-03-27

## 目标
- 让 Task 0.5 不停留在“新表骨架”层。
- 补上旧结构到新真相源的正式写入层，开始具备后续 `cutover` 的基础。

## 本轮执行

### 1. 社区层 reconciliation 写入服务落地
- 新增：
  - `backend/app/services/community/truth_source_sync_service.py`
- 已实现：
  - `community_pool/community_cache`
    -> `community_registry/community_domain_membership/community_governance_decision/community_runtime_state`
  - 写入方式是正式 upsert/sync，不是一次性 SQL 补丁
- 同时补了一个长期该有但之前缺失的正式模型：
  - `backend/app/models/business_category.py`

### 2. 语义层 reconciliation 写入服务落地
- 新增：
  - `backend/app/services/semantic/semantic_observation_sync.py`
- 已实现：
  - `post_semantic_labels`
  - `post_llm_labels`
  - `comment_llm_labels`
  - `content_labels`
  - `content_entities`
    统一归并写入 `semantic_observation`
- 这意味着：
  - 语义层不再只有设计口径，已经有正式统一账本入口

### 3. 定向测试补齐
- 新增：
  - `backend/tests/services/community/test_truth_source_sync_service.py`
  - `backend/tests/services/semantic/test_semantic_observation_sync.py`
- 同时继续保留：
  - `backend/tests/models/test_truth_source_models.py`
  - `backend/tests/services/community/test_truth_source_reconciler.py`

## 验证

- 命令：
  - `cd backend && SKIP_DB_RESET=1 ../.venv/bin/python -m pytest tests/models/test_truth_source_models.py tests/services/community/test_truth_source_reconciler.py tests/services/community/test_truth_source_sync_service.py tests/services/semantic/test_semantic_observation_sync.py -q`
- 结果：
  - `12 passed`

## 遇到的冲突与处理

### 1. `business_categories` 没有正式 ORM 模型
- 暴露方式：
  - 新的 `community_domain_membership.domain_key -> business_categories.key` 外键在测试建表阶段无法解析
- 处理：
  - 补正式模型 `BusinessCategory`
- 结论：
  - 这不是测试偶发问题，而是旧 DB 架构里一个真实的“核心表没有正式模型”的脏点

### 2. `community_cache` 现有测试库数据与定向测试撞车
- 暴露方式：
  - `r/parenting / r/daddit` 在 test 数据里已有残留，导致 `unique violation`
- 处理：
  - 在定向测试里显式清理 legacy rows
- 结论：
  - 不是 sync service 逻辑错，是测试数据环境脏，需要明确隔离

### 3. `semantic_observation.confidence` 口径不统一
- 暴露方式：
  - `content_labels.confidence=90` 直接写入 `NUMERIC(5,4)` 发生溢出
- 处理：
  - 在 sync service 中统一做 confidence 归一化：
    - `>1` 自动按百分比转小数
    - 最终 clamp 到 `0.9999`
- 结论：
  - 这一步很关键，因为它说明旧语义源的置信度口径本来就不统一，统一账本必须负责收口

## 四问回顾
1. 发现了什么？
- 只建新表不够，必须有正式 reconciliation 写入层，Task 0.5 才算真正开始工作。

2. 是否需要修复？
- 需要，而且这轮已经修到了“可写入、可测试”的程度。

3. 精确修复方法？
- 社区层：`truth_source_sync_service`
- 语义层：`semantic_observation_sync`
- 辅助补齐：`BusinessCategory` 正式模型

4. 下一步系统性计划是什么？
- 把这两套 sync 接进：
  - reconciliation 批处理
  - preflight/readiness
  - 主链切读

5. 这次执行的价值是什么？
- DB/语义真相源重构已经从“schema 重构”进入“数据迁移与统一写入口”阶段。
- 现在离真正的 `cutover` 已经更近，不再只是纸面设计。
