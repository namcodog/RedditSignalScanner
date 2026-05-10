# Phase 318 - 第三轮继续打磨：execute_target 异常收尾链拆分

## 1. 发现了什么？

- `execute_target_workflow.py` 里还残留了第三轮下一块很重的耦合点：
  - `timeout`
  - `budget_exhausted`
  - `execute_failed`
- 这三段异常链之前还在主 workflow 里自己背：
  - `mark_crawl_attempt(...)`
  - `mark_backfill_status_only(...)`
  - rollback / commit
  - partial / failed 持久化
  - compensation target 入队
- 大白话说：
  - **主 workflow 还在一边执行抓取，一边亲手处理整条错误收尾链。**

## 2. 是否需要修复？

- 需要，而且已经修完。
- 这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增独立 error workflow

新增：

- `backend/app/services/crawl/execute_target_error_workflow.py`

正式收了：

- `ExecuteTargetErrorInput`
- `ExecuteTargetErrorDeps`
- `ExecuteTargetErrorResult`
- `finalize_execute_target_error(...)`

现在统一承接三类错误收尾：

- `timeout`
- `budget_exhausted`
- `execute_failed`

把原来分散在主 workflow 里的这些动作都收回到独立齿轮：

- subreddit crawl attempt 标记
- backfill ERROR 状态更新
- rollback / commit
- partial / failed 状态落库
- compensation target 入队

### 3.2 收薄 execute_target_workflow

修改：

- `backend/app/services/crawl/execute_target_workflow.py`

现在：

- timeout 分支不再自己手搓整套 partial + compensation 链
- 限流分支不再自己手搓 budget exhausted 收尾链
- execute error 分支不再自己手搓 failed 持久化链
- 统一改成委托给 `finalize_execute_target_error(...)`

也就是：

- **主 workflow 继续往“只负责执行主线”的方向收薄**

### 3.3 测试门禁

新增：

- `backend/tests/services/crawl/test_execute_target_error_workflow.py`

覆盖：

- timeout -> partial + compensation
- budget exhausted -> partial + backfill error + compensation
- execute failed -> failed 且不生成 compensation

补充：

- `backend/tests/tasks/test_execute_target_task.py`

新增 task 兼容测试，锁住：

- execute error 仍会把 target 标成 `failed`
- 不会偷偷生成 compensation target

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_execute_target_error_workflow.py \
  tests/services/crawl/test_execute_target_followup.py \
  tests/services/crawl/test_execute_target_workflow.py \
  tests/tasks/test_execute_target_task.py -q
```

结果：

- `25 passed`

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/execute_target_error_workflow.py \
  backend/app/services/crawl/execute_target_workflow.py \
  backend/tests/services/crawl/test_execute_target_error_workflow.py \
  backend/tests/tasks/test_execute_target_task.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

- 现在 `execute_target` 这条执行主链，不再继续把三段最重的异常收尾背在自己身上。
- 数据采集模块的主 workflow 更像真正的执行中枢，错误收尾开始有独立齿轮。
- 这一步继续把第三轮往 `95+` 的目标推进：
  - 职责更清楚
  - 主 workflow 更薄
  - 错误收尾合同更稳
  - 后面再改 timeout / 限流 / execute_failed，不会再把主执行链一起拖回去

一句大白话：

- **这刀把数据采集模块里最后一大坨异常收尾链也拆成独立齿轮了，第三轮还在稳稳往 95 分以上推进。**
