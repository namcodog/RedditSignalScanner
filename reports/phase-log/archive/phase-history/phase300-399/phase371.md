# Phase 371 - 第三轮大包推进：IncrementalCrawler 运行时整组收口

## 1. 发现了什么？

这次没有再碎拆一个 helper，而是把 `IncrementalCrawler` 身上还挂着的一整组运行时方法一起抽掉了。

之前这个入口类虽然已经比前面薄了很多，但它还自己背着这些重逻辑：

- 增量 / comprehensive workflow deps 装配
- spam 判定与批量过滤
- 内容重复查重
- watermark 读取
- 冷热双写
- 冷库 upsert
- 热缓存 upsert
- crawl metrics 落地

另外还照出了一个真实 bug：

- `BlacklistConfig` 加载成功后，`self.blacklist` 仍然会被立刻重置成 `None`

也就是说，`IncrementalCrawler` 还不是纯入口壳，黑名单也没有真正生效到底。

## 2. 是否需要修复？

需要，而且这次已经成组修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增统一运行时层

新增：

- `backend/app/services/crawl/incremental_crawler_runtime.py`

正式收了：

- `IncrementalCrawlerRuntimeInput`
- `IncrementalCrawlerRuntime`
- `build_incremental_workflow_deps()`
- `build_comprehensive_workflow_deps()`
- `is_spam_post()`
- `filter_spam_posts()`
- `find_content_duplicate()`
- `get_watermark()`
- `dual_write()`
- `upsert_to_cold_storage()`
- `upsert_to_hot_cache()`
- `record_crawl_metrics()`

### 3.2 收薄 IncrementalCrawler

调整：

- `backend/app/services/crawl/incremental_crawler.py`

现在 `IncrementalCrawler` 的职责更清楚了：

- `__init__()` 负责装配 runtime
- 对外 public API 继续保留
- 旧的 `_get_watermark / _dual_write / _upsert_to_* / _record_crawl_metrics` 这些 seam 继续保留成薄委托，兼容现有测试和调用方

### 3.3 修掉 blacklist 真 bug

修复：

- `BlacklistConfig` 成功加载后，不再被 `self.blacklist = None` 覆盖

这条不是“顺手优化”，而是实打实的运行时 bug 修复。

### 3.4 补测试锁边界

新增：

- `backend/tests/services/crawl/test_incremental_crawler_runtime.py`

覆盖：

- runtime build 的 workflow deps 保持 `trigger_comments_fetch=True` 口径
- `IncrementalCrawler` 会真正保留已加载的 blacklist

并继续跑通原有成组回归：

- `test_incremental_crawler_deps_factory.py`
- `test_incremental_crawl_workflow.py`
- `test_comprehensive_crawl_workflow.py`
- `test_incremental_content_filter_service.py`
- `test_incremental_crawler_metrics.py`
- `test_incremental_crawler_run_id.py`
- `test_incremental_crawler_dedup.py`

## 4. 验证结果

### 4.1 成组定向回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_crawler_runtime.py \
  tests/services/crawl/test_incremental_crawler_deps_factory.py \
  tests/services/crawl/test_incremental_crawl_workflow.py \
  tests/services/crawl/test_comprehensive_crawl_workflow.py \
  tests/services/crawl/test_incremental_content_filter_service.py \
  tests/services/crawl/test_incremental_crawler_metrics.py \
  tests/services/crawl/test_incremental_crawler_run_id.py \
  tests/services/crawl/test_incremental_crawler_dedup.py -q
```

结果：

- `32 passed`

### 4.2 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/crawl/incremental_crawler.py \
  backend/app/services/crawl/incremental_crawler_runtime.py \
  backend/tests/services/crawl/test_incremental_crawler_runtime.py
```

结果：

- 通过

### 4.3 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 结果变化

文件规模：

```bash
wc -l \
  backend/app/services/crawl/incremental_crawler.py \
  backend/app/services/crawl/incremental_crawler_runtime.py \
  backend/app/services/report/report_service.py \
  backend/app/tasks/llm_label_task.py
```

结果：

- `incremental_crawler.py`: `543`
- `incremental_crawler_runtime.py`: `280`
- `report_service.py`: `191`
- `llm_label_task.py`: `186`

这说明第三轮现在已经不是“拆个小 seam”，而是在把主入口真正压到产品级可维护体量。

## 6. 当前完成度判断

我的最新判断：

- 第三轮完成度：约 `85%`
- 系统整体完成度：约 `92%-93%`

离 `95+` 还差最后几包封板：

1. `facts / 报告模块` 剩余 request / assembly seam
2. `语义 / 标签模块` 剩余 sync / import-export 接缝
3. `数据采集模块` 剩余极少数 wrapper / side-effect 清尾

## 7. 这次执行的价值是什么？达到了什么目的？

这次最值钱的不是“又拆了几个函数”，而是：

- `IncrementalCrawler` 终于不再自己背一整组运行时方法
- 黑名单真 bug 被顺手收掉
- 数据采集模块第三轮的“大包封板”开始成形

一句大白话总结：

- 这次是真的把 `IncrementalCrawler` 从“入口 + 一堆亲手干活”继续压成了“入口壳 + 独立齿轮协作”。
