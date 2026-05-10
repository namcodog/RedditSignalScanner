# Phase 364 - execute_crawl_plan deps 装配链抽离

## 1. 发现了什么？

这一步第三轮继续打的是数据采集模块里还留在总入口上的一大段 wiring：

- `backend/app/services/crawl/execute_plan.py`

虽然前面已经把：

- patrol workflow
- backfill_posts workflow
- seed_archive workflow
- probe workflow
- backfill_comments workflow

都拆成独立齿轮了，但 `execute_crawl_plan(...)` 还在自己手工拼一整份 `CrawlPlanDispatchDeps(...)`：

- workflow 入口函数
- `IncrementalCrawler` 注入
- backfill comments 的 resolve / count / persist / classify / entity extract 这套 wiring

大白话说：

- 总入口虽然已经不跑主链了
- 但“调度依赖怎么接起来”这件事还没有自己的正式真相源

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 execute plan deps factory

新增：

- `backend/app/services/crawl/execute_plan_deps_factory.py`

正式收了：

- `ExecuteCrawlPlanDepsFactoryInput`
- `build_execute_crawl_plan_dispatch_deps(...)`

现在这块统一负责：

- patrol / backfill_posts / seed_archive / probe / backfill_comments 的 workflow wiring
- `crawler_factory` 的统一注入
- backfill comments 那套 resolve / count / persist / classify / entity extract 的统一注入

### 3.2 收薄 execute_plan 入口

更新：

- `backend/app/services/crawl/execute_plan.py`

现在 `execute_crawl_plan(...)` 不再自己手工维护整份 `CrawlPlanDispatchDeps(...)`，而是变成薄委托：

1. 组装 `CrawlPlanDispatchInput`
2. 组装 `ExecuteCrawlPlanDepsFactoryInput`
3. 调 `build_execute_crawl_plan_dispatch_deps(...)`
4. 把结果交给 `dispatch_crawl_plan(...)`

也就是说：

- 总入口又薄了一层
- dispatcher wiring 开始也有自己的正式齿轮了

### 3.3 新增定向测试

新增：

- `backend/tests/services/crawl/test_execute_plan_deps_factory.py`

锁住两件事：

- patrol / backfill_posts / seed_archive 这三条链确实共用同一个 `crawler_factory`
- backfill comments 的五个依赖确实稳定透传到 `BackfillCommentsWorkflowDeps`

同时继续保留并跑通：

- `backend/tests/services/crawl/test_execute_crawl_plan_guardrails.py`
- `backend/tests/services/crawl/test_crawl_plan_dispatcher.py`
- `backend/tests/services/crawl/test_patrol_workflow.py`
- `backend/tests/services/crawl/test_backfill_posts_plan_workflow.py`

## 4. 测试与验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_execute_plan_deps_factory.py \
  tests/services/crawl/test_execute_crawl_plan_guardrails.py \
  tests/services/crawl/test_crawl_plan_dispatcher.py \
  tests/services/crawl/test_patrol_workflow.py \
  tests/services/crawl/test_backfill_posts_plan_workflow.py -q
```

结果：

- `9 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `execute_crawl_plan(...)` 里“调度依赖怎么接起来”这条链，现在开始也有自己的独立齿轮了
- 后面再改：
  - workflow 注入
  - crawler factory
  - backfill comments wiring
  就不容易再把总入口一起拖重

一句大白话：

- 这一步不是修小毛病，而是把数据采集模块里还留在总入口上的一大段 dispatcher wiring 正式抽开了。
