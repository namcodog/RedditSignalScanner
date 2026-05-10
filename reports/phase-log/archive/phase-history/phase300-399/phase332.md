# Phase 332 - 第三轮：seed crawl runner fallback workflow 拆分

## 1. 发现了什么？

第三轮继续推进数据采集模块时，`crawler_task.py` 里 `seed` 抓取主链还残留一段很重的 runner：

- 首次抓取
- 空集后 widen / relax 重试
- exhausted 后 unfiltered 重试
- fallback 异常吞掉并回原结果

大白话说：

- `_crawl_seeds_impl()` 虽然前面已经把 metrics 和 planner-only 逻辑拆薄了
- 但每个社区那条“首次抓取 + fallback 重试”的 runner 还缠在 task 壳里

这会让 `crawler_task` 继续背半套执行细节，不符合第三轮“task 壳继续变薄、workflow 继续独立”的目标。

## 2. 是否需要修复？

需要，而且已经修完。

本次没有改数据库表结构，没有新增 migration。

## 3. 精确修复方法？

### 3.1 新增独立 workflow

新增：

- `backend/app/services/crawl/seed_crawl_runner_workflow.py`

正式收了：

- `SeedCrawlRunnerWorkflowInput`
- `SeedCrawlRunnerWorkflowDeps`
- `run_seed_crawl_with_fallback(...)`

这条 workflow 统一承接：

- 首次抓取
- widen / relax fallback
- unfiltered fallback
- fallback 异常吞掉后回主结果

### 3.2 收薄 task 壳

修改：

- `backend/app/tasks/crawler_task.py`

现在 `_crawl_seeds_impl()` 里的 `runner(profile)` 不再自己手工维护整条 fallback 链，而是统一委托给 `run_seed_crawl_with_fallback(...)`。

直观结果：

- `crawler_task.py` 从 `1105` 行降到 `1044` 行

### 3.3 先补测试，再锁合同

新增：

- `backend/tests/services/crawl/test_seed_crawl_runner_workflow.py`

覆盖：

- 首次抓取成功时不误重试
- widen / relax fallback 生效
- unfiltered fallback 生效

同时保留并复跑：

- `backend/tests/tasks/test_crawler_fallback.py`

确保 task 层整体口径仍然是当前真实世界，不会因为 workflow 拆分而漂回去。

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_seed_crawl_runner_workflow.py \
  tests/tasks/test_crawler_fallback.py \
  tests/services/crawl/test_seed_crawl_metrics_service.py -q
```

结果：

- `7 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/seed_crawl_runner_workflow.py \
  backend/app/tasks/crawler_task.py \
  backend/tests/services/crawl/test_seed_crawl_runner_workflow.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `seed crawl` 里“首次抓取 + fallback 重试”现在开始有自己的独立齿轮了
- `_crawl_seeds_impl()` 更像真正的编排层
- 数据采集模块继续往“主 task 变薄、执行链独立”的方向收口

这继续沿着第三轮统一目标往前推：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

一句大白话：

- **这刀把 `seed` 抓取里最容易继续缠在 task 壳上的 fallback runner 正式抽成了独立 workflow，第三轮又稳稳往前推了一步。**
