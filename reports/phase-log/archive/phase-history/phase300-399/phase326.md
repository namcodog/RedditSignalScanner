# Phase 326 - 第三轮：数据采集模块继续拆 execute_target 后置触发器

## 1. 发现了什么？

这次第三轮继续打的是 `execute_target` 主链后面还缠在 task 壳里的两条触发器副作用：

- probe 成功后自动触发 evaluator
- `candidate_vetting` 回填后自动触发候选社区检查

之前这两条链虽然逻辑不长，但都还挂在 `crawl_execute_task.py` 里。大白话说就是：

- task 壳还在亲手判断“什么情况下要触发后置任务”
- 这会继续让任务入口知道太多业务细节

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库表结构，没有新 migration。
改的是数据采集模块里 `execute_target` 的后置触发器边界、依赖注入方式和测试门禁。

## 3. 精确修复方法？

这次做了三件事：

- 新增独立触发器 service：
  - `backend/app/services/crawl/execute_target_trigger_service.py`
  - 正式收了：
    - `ExecuteTargetTriggerDeps`
    - `should_auto_trigger_evaluator(...)`
    - `auto_trigger_evaluator_best_effort(...)`
    - `maybe_trigger_candidate_vetting_check(...)`

- 把 `backend/app/tasks/crawl_execute_task.py` 收成更薄的依赖注入口：
  - task 不再自己维护这两条触发器逻辑
  - 改成统一组装 `ExecuteTargetTriggerDeps`
  - 再用 `partial(...)` 注入到 follow-up workflow

- 补服务层测试并锁住当前真实合同：
  - `backend/tests/services/crawl/test_execute_target_trigger_service.py`
  - 覆盖：
    - 只有 `probe + discovered_communities_upserted > 0` 才允许自动触发 evaluator
    - 环境变量关闭时不会触发
    - 只有 `backfill_posts + candidate_vetting` 才会触发候选社区检查

## 4. 验证结果

- 定向回归：
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/crawl/test_execute_target_trigger_service.py tests/services/crawl/test_execute_target_followup.py tests/services/crawl/test_execute_target_workflow.py tests/tasks/test_execute_target_task.py -q`
  - `25 passed`

- 语法自检：
  - `python -m py_compile backend/app/services/crawl/execute_target_trigger_service.py backend/app/tasks/crawl_execute_task.py backend/tests/services/crawl/test_execute_target_trigger_service.py`
  - 通过

- 主门禁：
  - `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这次最值钱的地方很直接：

- `execute_target` 后面“什么时候自动触发后置任务”这件事，现在开始只有一个正式真相源了
- task 壳继续变薄
- follow-up workflow 继续往“独立齿轮”走

一句大白话收口：

- 这刀把 `execute_target` 主链后面还缠着的两条触发器副作用也拆开了，第三轮推进是稳的，而且没有口径漂移。
