# Phase 366 - IncrementalCrawler 运行时辅助链二次成组收口

## 1. 发现了什么？

这一步第三轮继续按“成组推进”打的是数据采集模块里还留在 `IncrementalCrawler` 身上的运行时辅助链：

- `backend/app/services/crawl/incremental_crawler.py`

前面虽然已经把：

- incremental/comprehensive crawl workflow
- dual write
- cold/hot storage
- crawl metrics

都拆成独立齿轮了，但 `IncrementalCrawler` 里还散着一整组运行时 helper：

- author upsert
- failure / empty attempt 记录
- score refresh 派发
- comments backfill 派发
- posts_latest refresh 派发
- watermark 更新

大白话说：

- 入口类已经薄了很多
- 但这些“运行时辅助主链”还没有自己的正式真相源

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 runtime deps factory

新增：

- `backend/app/services/crawl/incremental_runtime_deps_factory.py`

正式收了：

- `IncrementalRuntimeDepsFactoryInput`
- `IncrementalRuntimeDeps`
- `build_incremental_runtime_deps(...)`

现在这块统一负责：

- author upsert
- failure / empty attempt 记录
- score refresh 派发
- comments backfill 派发
- posts_latest refresh 派发
- watermark 更新

### 3.2 成组收薄 IncrementalCrawler

更新：

- `backend/app/services/crawl/incremental_crawler.py`

现在 `IncrementalCrawler.__init__()` 会先构建一份 `self._runtime_deps`，后面这些链都统一改成吃这份 runtime deps：

- `_incremental_crawl_workflow_deps()`
- `_comprehensive_crawl_workflow_deps()`
- `_dual_write()`
- `_upsert_to_cold_storage()`
- `_upsert_to_hot_cache()`

同时删掉了原来散在类里的几段 helper：

- `_record_incremental_failure_attempt`
- `_record_incremental_empty_attempt`
- `_dispatch_incremental_score_refresh`
- `_ensure_author`
- `_enqueue_comment_backfill`
- `_schedule_posts_latest_refresh`
- `_update_watermark`

也就是说：

- 这次不是只拆一个小口子
- 而是把一整组会反复拖重入口的辅助链一起挪回服务层

### 3.3 新增定向测试

新增：

- `backend/tests/services/crawl/test_incremental_runtime_deps_factory.py`

锁住三件事：

- `ensure_author` 的原子 upsert 合同
- failure / empty / watermark 三条 cache-status 链确实稳定吃到同一个 `db`
- score refresh / posts_latest refresh / comments backfill 三条 followup 派发确实稳定吃到同一个 `send_task`

同时继续保留并跑通：

- `backend/tests/services/crawl/test_incremental_crawl_workflow.py`
- `backend/tests/services/crawl/test_comprehensive_crawl_workflow.py`
- `backend/tests/services/crawl/test_incremental_post_persistence_service.py`
- `backend/tests/services/crawl/test_incremental_cold_storage_service.py`
- `backend/tests/services/crawl/test_incremental_hot_cache_service.py`

## 4. 测试与验证

### 成组定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_runtime_deps_factory.py \
  tests/services/crawl/test_incremental_crawl_workflow.py \
  tests/services/crawl/test_comprehensive_crawl_workflow.py \
  tests/services/crawl/test_incremental_post_persistence_service.py \
  tests/services/crawl/test_incremental_cold_storage_service.py \
  tests/services/crawl/test_incremental_hot_cache_service.py -q
```

结果：

- `16 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_runtime_deps_factory.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_runtime_deps_factory.py
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

- `IncrementalCrawler` 里一整组运行时辅助链，现在开始只有一个正式真相源了
- 后面再改：
  - author upsert
  - watermark
  - failure / empty 记录
  - score refresh
  - comments backfill
  - posts_latest refresh
  就不容易再把入口类一起拖重

一句大白话：

- 这一步不是修一个小口子，而是把数据采集模块里一整组会反复拖重入口的运行时辅助链一起抽回服务层了。
