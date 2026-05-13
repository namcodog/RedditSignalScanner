# Phase 573 - Hotpost 去工程化第一刀：最小持久化

## 1. 发现了什么？
- `hotpost` 现在已经有明显工程化过头的迹象：
  - 后端搜索完成后，不只写结果缓存，还会顺手：
    - 写 `EvidencePost`
    - 写 `HotpostQueryEvidenceMap`
    - 写 `hotpost:comments:*`
    - 写 `hotpost:llm_report:*`
    - 写 `DiscoveredCommunity`
- 但当前小程序真实在用的链路其实只有：
  - `POST /api/v1/hotpost/search`
  - `GET /api/v1/hotpost/result/{query_id}`
  - 本机历史存储 `hotpost:history`
- 小程序历史页和详情回看都走本地缓存，不依赖后端这些额外账本。

## 2. 是否需要修复？
- 需要。
- 这轮不是补结果，而是先把 `hotpost` 收回轻业务边界：
  - 保留实时结果
  - 保留最小 query 记录
  - 砍掉不直接服务当前体验的副作用写入

## 3. 精确修复方法？
- 已修改：
  - `backend/app/services/hotpost/persistence_workflow.py`
  - `backend/tests/services/hotpost/test_persistence_workflow.py`
- 当前 `persist_hotpost_search_side_effects()` 已收成最小集合：
  - 只更新 `HotpostQuery`
  - 只写：
    - 主缓存 key
    - `hotpost:result:{query_id}`
- 已删除这层实际执行的副作用：
  - `EvidencePost` upsert
  - `HotpostQueryEvidenceMap` 插入
  - `hotpost:comments:*`
  - `hotpost:llm_report:*`
  - `DiscoveredCommunity` 发现写入

## 4. 验证
- `pytest backend/tests/services/hotpost/test_persistence_workflow.py -q`
  - `2 passed`
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_hotpost_retrieval_precision.py backend/tests/services/hotpost/test_hotpost_detail_builder.py backend/tests/services/hotpost/test_hotpost_query_resolver.py backend/tests/services/hotpost/test_hotpost_preview_projection.py backend/tests/services/hotpost/test_hotpost_response_bundle.py backend/tests/services/hotpost/test_hotpost_mode_contract.py backend/tests/services/hotpost/test_hotpost_search_workflow.py backend/tests/services/hotpost/test_hotpost_search_service.py backend/tests/services/hotpost/test_persistence_workflow.py -q`
  - `61 passed`

## 5. 这次执行的价值是什么？
- `hotpost` 现在朝着 `hotpost-lite` 真正走了一步：
  - 少写一堆当前没人消费的后台账本
  - 少一层耦合
  - 少一层状态复杂度
- 更重要的是，这一刀没有误伤 `trending` 或小程序当前主链。
- 下一步应该继续收：
  1. `create/update query + queue` 是否还能再缩
  2. `deepdive` 是否保留为可选，而不是主链刚需
  3. 把节省出来的复杂度预算重新投到 `query/retrieval/expression`，只服务 100 分结果
