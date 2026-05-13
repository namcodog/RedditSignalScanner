# Phase 331 - 第三轮：语义/标签模块抽离标签结果持久化服务

## 1. 发现了什么？

第三轮继续推进语义/标签模块时，`llm_label_task.py` 里还残留一段很容易继续缠回 task 壳的逻辑：

- post/comment 标签行构造
- `post_llm_labels` / `comment_llm_labels` upsert
- `sync_llm_terms(...)` 语义词同步

大白话说：

- task 壳虽然已经不再自己做候选规划和 batch orchestration 了
- 但“标签结果怎么真正落库并同步语义词”这件事，还没完全回到服务层

这会带来两个风险：

- 在线 post/comment 两条增量链继续在 task 层背半套写库编排
- 后面再改标签元数据或同步口径时，容易继续在 task/helper 里漂

## 2. 是否需要修复？

需要，而且已经修完。

本次没有改数据库表结构，没有新增 migration。

## 3. 精确修复方法？

### 3.1 新增公共持久化服务

新增：

- `backend/app/services/llm/label_result_persistence.py`

正式收了：

- `LabelResultPersistenceDeps`
- `build_default_label_result_persistence_deps()`
- `persist_incremental_post_analysis(...)`
- `persist_incremental_comment_analysis(...)`

这层现在统一承接：

- 标签行构造
- `post/comment llm labels` upsert
- `sync_llm_terms(...)` 语义词同步

### 3.2 收薄 task 壳

修改：

- `backend/app/tasks/llm_label_task.py`

现在：

- 在线 post 增量链直接用 `persist_incremental_post_analysis`
- 在线 comment 增量链直接用 `persist_incremental_comment_analysis`

task 不再继续维护：

- `_persist_post_analysis`
- `_persist_comment_analysis`

只保留 legacy backfill 还需要的薄 upsert helper，不让第三轮这刀把历史回填口径一起带歪。

直观结果：

- `llm_label_task.py` 从 `409` 行降到 `348` 行

### 3.3 先补测试，再锁合同

新增：

- `backend/tests/services/llm/test_label_result_persistence.py`

覆盖：

- post 标签结果会正确 upsert 并同步语义词
- comment 标签结果会正确 upsert 并同步语义词
- 缺失 post row 时会明确报错，不再静默跳过

同时更新：

- `backend/tests/tasks/test_llm_label_task.py`

让 task 层测试改为 patch 新的公共持久化函数，而不是继续 patch 旧的 task 私有 helper。

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_label_result_persistence.py \
  tests/tasks/test_llm_label_task.py \
  tests/services/llm/test_post_label_workflow.py \
  tests/services/llm/test_comment_label_workflow.py \
  tests/services/llm/test_legacy_label_backfill_workflow.py -q
```

结果：

- `16 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/label_result_persistence.py \
  backend/app/tasks/llm_label_task.py \
  backend/tests/services/llm/test_label_result_persistence.py \
  backend/tests/tasks/test_llm_label_task.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `llm_label_task` 里“标签结果怎么落库并同步语义词”现在开始有自己的公共齿轮了
- 在线 post/comment 两条链开始吃同一套持久化合同
- task 壳继续变薄，更像真正的编排入口

这继续沿着第三轮统一目标往前推：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

一句大白话：

- **这刀把语义/标签模块里还留在 task 壳上的“结果落库 + 语义词同步”这套动作正式抽成了公共服务，第三轮又稳稳往前推了一步。**
