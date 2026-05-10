# Phase 324 - 第三轮：数据采集模块补平 low-quality planner 合同

## 1. 发现了什么？

- 第三轮继续拆数据采集模块时，`low_quality planner` 这刀已经落了一半，但还留了两个真实断点：
  - `plan_low_quality_communities_workflow(...)` 新增了 `total` 合同，却没有把 `total` 真正带出来。
  - `tests/services/crawl/test_planner_workflow.py` 的 `_reset_tables()` 只清了 `task_outbox / crawler_run_targets / crawler_runs`，没有清 `community_cache`。
- 结果就是：
  - `low_quality` 那条测试会拿到 `total=None`
  - `seed_sampling` 那条测试会被脏 `community_cache` 放大，planner 选进额外社区，断言 `inserted_count == 2` 时变成 `0 == 2`

大白话：

- 这次不是主逻辑设计翻车
- 而是“新合同加了一半 + 测试隔离没跟上当前真实世界”

## 2. 是否需要修复？

- 需要。
- 这一步必须补平，不然第三轮这刀还是半成品：
  - 代码口径没完全统一
  - 测试也没真正锁住当前真实合同

## 3. 精确修复方法？

### 3.1 补平 low-quality planner 的结果合同

- 修改：
  - `backend/app/services/crawl/planner_workflow.py`

把 `plan_low_quality_communities_workflow(...)` 的返回补齐：

- `total=len(communities)`

这样 task 壳和 workflow 终于用的是同一套 planner 结果语言：

- `status`
- `inserted`
- `enqueued`
- `run_id`
- `total`

### 3.2 把 planner 测试拉回当前真实隔离

- 修改：
  - `backend/tests/services/crawl/test_planner_workflow.py`

把 `_reset_tables()` 补成同时清：

- `task_outbox`
- `crawler_run_targets`
- `crawler_runs`
- `community_cache`

原因很直接：

- 当前 `seed_sampling` 和 `low_quality` planner 都会直接扫 `community_cache`
- 如果不清这里，测试就会被库里残留 cache 放大
- 断言看起来像主逻辑坏了，实际上只是测试环境不干净

一句大白话：

- 这次补的是“planner 结果合同 + planner 测试隔离”这两个真断点

## 4. 验证结果

### 先跑两个断点用例

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_planner_workflow.py::test_plan_seed_sampling_workflow_enqueues_capped_only \
  tests/services/crawl/test_planner_workflow.py::test_plan_low_quality_communities_workflow_enqueues_stale_low_quality_only \
  -q
```

结果：

- `2 passed`

### 再跑整组 planner 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_planner_workflow.py \
  tests/tasks/test_low_quality_planner_task.py \
  -q
```

结果：

- `4 passed`

### 语法检查

```bash
python -m py_compile \
  backend/app/services/crawl/planner_workflow.py \
  backend/app/tasks/crawler_task.py \
  backend/tests/services/crawl/test_planner_workflow.py \
  backend/tests/tasks/test_low_quality_planner_task.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `low_quality planner` 这刀现在不再是半成品了
- planner workflow 的结果合同真正补平了
- planner 测试也重新回到了当前真实世界，不再被脏 cache 误导

当前直观结果：

- `backend/app/services/crawl/planner_workflow.py`：`345` 行
- `backend/app/tasks/crawler_task.py`：`1210` 行

一句大白话总结：

- 第三轮这一步，把数据采集模块里一块“已经拆了但没完全收口”的 planner 逻辑真正补平了，节奏没有乱，口径也没有漂。
