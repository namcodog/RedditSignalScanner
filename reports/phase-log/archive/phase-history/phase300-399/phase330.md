# Phase 330 - 第三轮：hotpost 持久化 side-effect workflow 拆分

## 1. 发现了什么？

第三轮继续推进 `hotpost` 模块时，`HotpostService.search()` 里还残留一段很重的 side-effect 主链：

- 证据帖写库
- `query -> evidence` 映射写库
- comments cache 落 Redis
- 社区发现写 `discovered_communities`
- query 结果更新
- 最终结果缓存 / LLM report 缓存

这段逻辑之前直接缠在主服务里，导致 `search()` 既负责取数和编排，又亲手做整段持久化与缓存落盘，不符合第三轮“主服务继续变薄、workflow 继续独立”的目标。

## 2. 是否需要修复？

需要，而且已经修完。

本次没有改数据库表结构，没有新增 migration。

## 3. 精确修复方法？

### 3.1 新增独立 workflow

新增：

- `backend/app/services/hotpost/persistence_workflow.py`

正式收了：

- `HotpostPersistenceWorkflowInput`
- `HotpostPersistenceWorkflowDeps`
- `HotpostPersistenceWorkflowResult`
- `persist_hotpost_search_side_effects(...)`

这条 workflow 统一承接：

- 证据帖 upsert
- query-evidence map 写入
- comments cache 写入
- community discovery 触发
- query 统计更新
- result / llm_report 缓存

### 3.2 收薄主服务

修改：

- `backend/app/services/hotpost/service.py`

现在 `search()` 不再自己维护整条持久化 side-effect 链，而是在生成 `HotpostSearchResponse` 后，统一委托给 `persist_hotpost_search_side_effects(...)`。

直观结果：

- `service.py` 从 `861` 行降到 `814` 行

### 3.3 先补测试，再锁合同

新增：

- `backend/tests/services/hotpost/test_persistence_workflow.py`

覆盖：

- 证据帖 / 映射 / comments cache / 结果缓存 / query 更新都能按当前合同写出
- 无 LLM report 时不会误写 `hotpost:llm_report:*`

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/hotpost/test_persistence_workflow.py \
  tests/services/hotpost/test_hotpost_summary_workflow.py \
  tests/services/hotpost/test_hotpost_response_bundle.py -q
```

结果：

- `8 passed`

### hotpost 整组回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost -q
```

结果：

- `55 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `hotpost` 里“查完结果后怎么落地到 DB / Redis”现在开始有自己的独立齿轮了
- `HotpostService` 更像真正的编排层，不再一边查数据一边自己手搓整条持久化链
- 第三轮继续沿着统一准则往前推：
  - 各模块职责清楚
  - 通过统一接口协同
  - 彼此少牵连
  - 整条链路顺畅可控

一句大白话：

- **这刀把 `hotpost` 主链里最后一段很重的持久化 side-effect 拆出来了，第三轮还在稳稳往 `95+` 推。**
