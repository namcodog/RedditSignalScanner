# Phase 574 - Hotpost 去工程化第二刀：Deepdive 与 Query Record 解耦

## 1. 发现了什么？
- `hotpost` 还有一条隐性耦合没有切干净：
  - `/api/v1/hotpost/deepdive`
  - 还在直接读 `HotpostQuery`
- 这意味着：
  - `hotpost` 想继续深挖，先得有数据库记录
  - `query record` 也就被反向绑成了运行时刚需
- 但当前真正已经稳定存在的真结果，其实就在：
  - `hotpost:result:{query_id}`

## 2. 是否需要修复？
- 需要。
- 这轮继续按 `hotpost-lite` 思路做：
  - 保留能力
  - 去掉数据库耦合
  - 不新增新层

## 3. 精确修复方法？
- 已修改：
  - `backend/app/api/v1/endpoints/hotpost.py`
  - `backend/app/services/hotpost/search_workflow.py`
  - `backend/app/services/hotpost/persistence_workflow.py`
  - `backend/tests/api/test_hotpost.py`
  - `backend/tests/services/hotpost/test_hotpost_search_workflow.py`
  - `backend/tests/services/hotpost/test_persistence_workflow.py`
- 当前新口径：
  1. `deepdive` 直接从 `hotpost:result:{query_id}` 读结果
     - 不再读 `HotpostQuery`
     - `seed_subreddits / time_filter / mode` 改从缓存结果和 `debug_info` 推出
  2. `search_workflow` 不再创建 `HotpostQuery`
  3. cache-hit 路径不再更新 `HotpostQuery`
  4. `persistence_workflow` 也不再更新 `HotpostQuery`

## 4. 验证
- `SKIP_DB_RESET=1 pytest backend/tests/api/test_hotpost.py -k deepdive -q`
  - `2 passed`
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_search_workflow.py backend/tests/services/hotpost/test_hotpost_search_service.py backend/tests/services/hotpost/test_persistence_workflow.py -q`
  - `20 passed`

## 5. 这次执行的价值是什么？
- `hotpost` 现在运行时已经进一步脱离数据库账本：
  - 继续深挖不再依赖 `HotpostQuery`
  - 搜索主链也不再默认写 query 流水
- 这意味着：
  - `hotpost` 更像实时轻工具
  - 而不是一套先写账本、再回头消费账本的小系统
- 下一步更合理的是：
  1. 再审 `stream/queue` 是否还是主链刚需
  2. 清理 `deps_factory / repository` 里残留但已不再参与运行的旧接线
  3. 把重心继续拉回 `query / retrieval / expression`
