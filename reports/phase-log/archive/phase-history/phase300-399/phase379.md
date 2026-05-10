# Phase 379 - 第三轮大包推进：crawler_task helper / support 成组收口

## 1. 发现了什么？

这次收的不是 `IncrementalCrawler`，而是它前面的 `crawler_task` 入口整包。

之前 `backend/app/tasks/crawler_task.py` 虽然已经拆过很多轮，但它还自己背着一整组 support/helper：

- 日志吞并
- commit / rollback 包装
- tier 解析
- 环境变量读取
- `crawler_run_targets` 表存在性检查
- planner lock
- probe hot fallback
- failure / empty hit 记录
- stale cache 查询

大白话说：

- 主链已经拆开了
- 但 `crawler_task.py` 还像一个“半大的总管”

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 support 模块

新增：

- `backend/app/services/crawl/crawler_task_support.py`

正式收了：

- `log_swallowed_exception(...)`
- `rollback_with_warning(...)`
- `commit_with_warning(...)`
- `tier_settings_for(...)`
- `env_truthy(...)`
- `env_int(...)`
- `crawler_run_targets_table_exists(...)`
- `planner_lock(...)`
- `load_last_probe_hot_started_at(...)`
- `maybe_trigger_probe_hot_fallback(...)`
- `mark_failure_hit(...)`
- `mark_empty_hit(...)`
- `list_stale_caches(...)`

### 3.2 收薄 crawler_task

调整：

- `backend/app/tasks/crawler_task.py`

现在这个文件主要只保留：

- Celery task 入口
- 少量兼容 seam
- 对 runtime / support 的薄委托

一个很直观的结果：

- `crawler_task.py` 从 `772` 行，压到了现在的 `670` 行

当前文件体量：

- `crawler_task.py`: `670`
- `crawler_task_support.py`: `268`

### 3.3 兼容口补平

这次整包推进里，顺手补平了 3 类兼容口：

1. `crawl_execute_task` 里的 `_should_auto_trigger_evaluator(...)`
2. `crawler_task` 里的 `CrawlMetrics`
3. `crawler_task` 里的 `TieredScheduler`

这些不是回退重构，而是保留旧 patch seam，让老测试继续能 patch 到当前真实边界。

另外还顺手把一条彻底过时的旧测试拉回了当前真相：

- `tests/tasks/test_incremental_crawl_tiers.py`

它之前还停在“增量抓取直接执行 crawler 主链”的旧世界。现在已经改成验证：

- 当前真实口径是 planner-only
- `_crawl_seeds_incremental_impl(...)` 只负责委托 `run_patrol_planner_task_runtime(...)`

## 4. 验证结果

### 4.1 crawler_task 成组回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_crawler_task_support.py \
  tests/tasks/test_crawler_fallback.py \
  tests/config/test_default_flags.py \
  tests/tasks/test_backfill_bootstrap_planner_task.py \
  tests/tasks/test_seed_sampling_planner_task.py \
  tests/tasks/test_patrol_planner_task.py \
  tests/tasks/test_incremental_crawl_tiers.py \
  tests/tasks/test_task_outbox_dispatcher_task.py -q
```

结果：

- `30 passed`

### 4.2 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.3 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/crawl/crawler_task_support.py \
  backend/app/tasks/crawler_task.py \
  backend/app/tasks/crawl_execute_task.py \
  backend/tests/services/crawl/test_crawler_task_support.py \
  backend/tests/tasks/test_incremental_crawl_tiers.py
```

结果：

- 通过

## 5. 当前完成度判断

这一步之后，我的判断是：

- 第三轮完成度：约 `94%-95%`
- 系统整体完成度：约 `96%-97%`

剩下真正值得继续打的大包，已经不多了，主要是：

1. 语义 / 标签模块最后一包清尾
2. 数据采集模块最后一小包清尾
3. 第三轮总复盘，判断是否正式站稳 `95+`

## 6. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `crawler_task.py` 不再自己背一整组 support/helper
- `probe fallback`、`planner lock`、`failure/empty hit`、`stale cache` 这些容易拖重入口的逻辑，现在开始只有一个正式真相源
- 后面再改这些规则，不容易再把 task 入口一起拖重

一句大白话总结：

- 这次把 `crawler_task` 这一整包真正抽开了，数据采集模块第三轮已经进入最后封板阶段。
