# Phase 524 - DB 真相源重构第一刀：新骨架落地

## 时间
- 2026-03-27

## 目标
- 不再在 `community_pool / community_cache` 上继续叠补丁。
- 先把新的社区真相源和语义真相源骨架正式落到代码与 migration。

## 本轮执行

### 1. 新社区真相源模型落地
- 新增：
  - `backend/app/models/community_registry.py`
  - `backend/app/models/community_domain_membership.py`
  - `backend/app/models/community_governance_decision.py`
  - `backend/app/models/community_runtime_state.py`
- 角色切分：
  - `community_registry`：社区身份
  - `community_domain_membership`：社区属于哪个领域
  - `community_governance_decision`：这个归属是否批准
  - `community_runtime_state`：运行态、水位、回填状态

### 2. 新语义真相源模型落地
- 新增：
  - `backend/app/models/semantic_observation.py`
- 目的：
  - 给后续 readiness / query expansion / report business translation 提供统一语义观测账本
  - 不再继续把 `post_semantic_labels / llm_labels / content_labels / content_entities` 当长期终态

### 3. migration 骨架落地
- 新增：
  - `backend/alembic/versions/20260327_000001_add_truth_source_registry_tables.py`
- 当前 migration head 已确认是：
  - `20260317_000001`
- 注意：
  - 本地未直接执行 `alembic current/upgrade`
  - 原因是当前 shell 未注入 `DATABASE_URL`
  - 但迁移文件和模型元数据已对齐

### 4. 旧表到新真相源的对齐规则固化
- 新增：
  - `backend/app/services/community/truth_source_reconciler.py`
  - `backend/tests/services/community/test_truth_source_reconciler.py`
- 当前已把旧结构到新结构的第一版映射规则收成纯函数：
  - `community_pool -> registry/membership/governance`
  - `community_cache -> runtime_state`
- 这一步的意义：
  - 后续 reconciliation、双写、导入脚本都不再各写各的映射逻辑

## 验证

- 命令：
  - `cd backend && SKIP_DB_RESET=1 ../.venv/bin/python -m pytest tests/models/test_truth_source_models.py tests/services/community/test_truth_source_reconciler.py -q`
- 结果：
  - `8 passed`

## 四问回顾
1. 发现了什么？
- 当前真正该做的不是继续修旧表，而是先把新真相源结构正式建立起来。

2. 是否需要修复？
- 需要，而且是架构重构，不是补丁。

3. 精确修复方法？
- 先落新表和 migration
- 再把旧表到新表的映射规则收成统一 reconciler
- 后续再做真正的 DB reconciliation / 双写 / 主链切换

4. 下一步系统性计划是什么？
- 继续推进 Task 0.5：
  - 做 reconciliation 写入层
  - 让 preflight/readiness 开始读新真相源

5. 这次执行的价值是什么？
- DB/语义真相源重构终于从“设计文档”进入“真实代码阶段”。
- 现在不是停留在口头说要拆层，而是已经有了可演进的新骨架。
