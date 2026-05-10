# Phase 325 - 第三轮：数据采集模块继续拆补偿目标链

## 1. 发现了什么？

- 第三轮继续打数据采集模块时，`crawl_execute_task.py` 里还残留着一条很重的补偿目标链：
  - 生成 compensation idempotency key
  - 计算人类可读 key
  - 计算 compensation delay
  - 创建 `crawler_run_targets`
  - 写 `task_outbox`
- 也就是说，虽然 `execute_target_workflow` 主链已经拆出来了，但：
  - **补偿目标怎么生成、怎么入队** 这件事，还是 task 私有实现。

大白话：

- 主链已经在变薄
- 但补偿副作用还没真正独立成自己的齿轮

## 2. 是否需要修复？

- 需要。
- 这是第三轮很典型的一刀：
  - 继续把“task 壳既编排又亲手跑副作用”的问题拆开
  - 让 `crawl_execute_task.py` 继续变薄
  - 让 compensation target 开始有自己的正式真相源

## 3. 精确修复方法？

### 3.1 新增独立 compensation service

- 新增：
  - `backend/app/services/crawl/compensation_target_service.py`

正式收了：

- `CompensationTargetDeps`
- `compute_compensation_idempotency_key(...)`
- `compute_compensation_idempotency_key_human(...)`
- `compute_compensation_delay_seconds(...)`
- `enqueue_compensation_target(...)`

职责固定为：

- 生成补偿 target 的标识
- 计算 delay 批次
- 创建 compensation `crawler_run_targets`
- 写对应的 `task_outbox`

### 3.2 `crawl_execute_task.py` 收成更薄

- 修改：
  - `backend/app/tasks/crawl_execute_task.py`

现在 task 层只负责：

- 组装 `CompensationTargetDeps`
- 把 `enqueue_compensation_target` 作为依赖传给 `ExecuteTargetWorkflowDeps`

不再自己维护整条补偿链。

### 3.3 补测试锁住新边界

- 新增：
  - `backend/tests/services/crawl/test_compensation_target_service.py`

重点锁了两件事：

- `backfill_posts` compensation target 能正确写 `crawler_run_targets + task_outbox`
- compensation delay 批次逻辑会在第二个补偿 target 开始生效

同时保留并回归了：

- `backend/tests/services/crawl/test_execute_target_error_workflow.py`
- `backend/tests/services/crawl/test_execute_target_followup.py`
- `backend/tests/tasks/test_execute_target_task.py`

确保这次拆分没有把原来的主链打坏。

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_compensation_target_service.py \
  tests/services/crawl/test_execute_target_error_workflow.py \
  tests/services/crawl/test_execute_target_followup.py \
  tests/tasks/test_execute_target_task.py \
  -q
```

结果：

- `26 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法检查

```bash
python -m py_compile \
  backend/app/services/crawl/compensation_target_service.py \
  backend/app/tasks/crawl_execute_task.py \
  backend/tests/services/crawl/test_compensation_target_service.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

这刀最值钱的地方很直接：

- `execute_target` 主链里“补偿目标怎么生成、怎么入队”现在开始只有一个正式真相源了
- `crawl_execute_task.py` 继续变薄
- `execute_target_workflow` / `error workflow` / `followup workflow` / `compensation service` 这几块开始更像能稳定咬合的齿轮

当前直观结果：

- `backend/app/services/crawl/compensation_target_service.py`：`219` 行
- `backend/app/tasks/crawl_execute_task.py`：`516` 行

一句大白话总结：

- 第三轮这一步，把数据采集模块里一条很重的补偿副作用链真正拆成了独立服务，task 壳又薄了一层，整机稳定性和可维护性都更进了一步。
