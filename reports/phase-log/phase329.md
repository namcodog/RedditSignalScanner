# Phase 329 - 第三轮：数据采集模块继续拆 seed crawl metrics 与 tier 分配链

## 1. 发现了什么？

这次第三轮继续打的是 `_crawl_seeds_impl()` 里还残留的一大段副作用链：

- 统计 `success / failed / empty / latency`
- 计算并应用 `tier_assignments`
- 写 `crawl_metrics`
- 先 upsert，失败再 fallback add

大白话说：

- 旧版 seed 抓取主链还在一边抓取，一边自己做整套 metrics/tier 后处理
- 这块虽然是兼容链，但还很重，也很容易继续把主入口拖回“大总管”状态

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库表结构，没有新 migration。  
改的是数据采集模块里 seed crawl metrics/tier 分配的 service 边界、旧兼容链主入口职责和测试门禁。

## 3. 精确修复方法？

这次做了三件事：

- 新增独立 service：
  - `backend/app/services/crawl/seed_crawl_metrics_service.py`
  - 正式收了：
    - `SeedCrawlMetricsInput`
    - `SeedCrawlMetricsDeps`
    - `SeedCrawlMetricsResult`
    - `record_seed_crawl_metrics(...)`
    - `build_default_seed_crawl_metrics_deps()`

- 把 `backend/app/tasks/crawler_task.py` 的 `_crawl_seeds_impl()` 收成更薄的主链：
  - 抓取完成后不再自己手工做 tier 分配和 crawl_metrics 落盘
  - 改成统一委托给 `record_seed_crawl_metrics(...)`

- 先补 service 测试，再把旧 fallback 测试拉回当前真实合同：
  - `backend/tests/services/crawl/test_seed_crawl_metrics_service.py`
  - `backend/tests/tasks/test_crawler_fallback.py`
  - 旧测试不再 patch 已经被拆走的 `TieredScheduler`
  - 改成 patch 新的 metrics service seam

## 4. 验证结果

- 定向回归：
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/crawl/test_seed_crawl_metrics_service.py tests/tasks/test_crawler_fallback.py -q`
  - `4 passed`

- 语法自检：
  - `python -m py_compile backend/app/services/crawl/seed_crawl_metrics_service.py backend/app/tasks/crawler_task.py backend/tests/services/crawl/test_seed_crawl_metrics_service.py backend/tests/tasks/test_crawler_fallback.py`
  - 通过

- 主门禁：
  - `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这次最值钱的地方很直接：

- 旧版 seed 抓取主链里“抓完以后怎么算 tier、怎么写 metrics”这件事，现在开始只有一个正式真相源了
- `_crawl_seeds_impl()` 继续变薄
- 即使是兼容链，也继续往“主入口只编排、不亲手干重活”的方向推进

一句大白话收口：

- 这刀把数据采集模块里旧版 seed 抓取后半段那条最重的 metrics/tier 副作用链拆开了，第三轮推进还是稳的。
