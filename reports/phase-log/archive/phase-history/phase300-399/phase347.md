# Phase 347 - 第三轮继续推进：Incremental Cache Status Service 独立化

## 本轮目标

继续第三轮结构性打磨，把 `IncrementalCrawler` 里三条还缠着的 cache 状态更新链拆成独立 service：

- failure attempt
- empty attempt
- watermark update

让抓取入口不再继续亲手维护 `community_cache` 的失败、空结果、水位线状态更新。

## 发现的问题

- `backend/app/services/crawl/incremental_crawler.py` 里的这三段方法之前还在自己背：
  - `_record_incremental_failure_attempt()`
  - `_record_incremental_empty_attempt()`
  - `_update_watermark()`
- 它们都直接在入口类里做：
  - `community_cache` upsert
  - 计数器更新
  - `last_attempt_at / last_crawled_at`
  - `last_seen_post_id / last_seen_created_at`
  - `total_posts_fetched / dedup_rate`
  - `commit`

大白话说：

- 抓取主链已经拆了很多刀，但“社区抓取状态怎么写回 cache”这组 side-effect 还没回到独立齿轮里。

## 修复动作

### 1. 新增独立 service

新增：

- `backend/app/services/crawl/incremental_cache_status_service.py`

正式收了：

- `FailureAttemptInput`
- `EmptyAttemptInput`
- `WatermarkUpdateInput`
- `IncrementalCacheStatusDeps`
- `record_incremental_failure_attempt(...)`
- `record_incremental_empty_attempt(...)`
- `update_incremental_watermark(...)`

这组 service 现在统一承接：

- failure `community_cache` upsert
- empty `community_cache` upsert
- watermark / dedup / fetched count 更新
- `commit`

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

现在这三段都改成薄委托：

1. 组装 input
2. 组装 deps
3. 调新 service

这意味着：

- `IncrementalCrawler` 不再亲手维护整条 cache 状态回写链
- 后面再改：
  - failure/empty hit 口径
  - 水位线字段
  - dedup_rate
  - fetched count
  不容易再把抓取入口一起拖重

### 3. 补测试并锁新边界

新增：

- `backend/tests/services/crawl/test_incremental_cache_status_service.py`

覆盖：

- failure attempt upsert
- empty attempt 计数更新
- watermark / total_posts_fetched / success_hit / dedup_rate 更新

继续保留并跑通 wrapper 合同测试：

- `backend/tests/services/crawl/test_incremental_crawler_metrics.py`

## 结果

- `IncrementalCrawler` 里 failure / empty / watermark 三条 cache 状态更新链，不再亲手维护
- `community_cache` 状态回写，现在开始有独立真相源
- 数据采集模块继续往“入口更薄、side-effect 更独立”推进

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_cache_status_service.py \
  tests/services/crawl/test_incremental_crawler_metrics.py -q
```

结果：

- `7 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_cache_status_service.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_cache_status_service.py
```

结果：

- 通过

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 当前判断

这一步是第三轮里一刀真正值钱的结构性收口：

- `IncrementalCrawler` 继续变薄
- cache 状态更新开始有独立齿轮
- 数据采集模块继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
