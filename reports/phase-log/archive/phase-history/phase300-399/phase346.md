# Phase 346 - 第三轮继续推进：Crawl Metrics Service 独立化

## 本轮目标

继续第三轮结构性打磨，把 `IncrementalCrawler._record_crawl_metrics()` 从入口类里拆成独立 service，让抓取指标统计、查询、upsert、提交不再继续挂在 crawler 入口上。

## 发现的问题

- `backend/app/services/crawl/incremental_crawler.py` 里的 `_record_crawl_metrics()` 之前还在自己背：
  - `posts_hot` 近 24h 计数
  - 活跃社区计数
  - `cache_hit_rate` 计算
  - `crawl_metrics` 按小时 upsert
  - `commit`
  - 日志口径
- 这让 `IncrementalCrawler` 继续同时承担：
  - 抓取入口
  - 双写编排
  - 水位线推进
  - 指标统计与落盘

大白话说：

- 抓取主链已经拆了很多刀，但“埋点怎么查、怎么算、怎么写”这条 side-effect 还没回到独立齿轮里。

## 修复动作

### 1. 新增独立 service

新增：

- `backend/app/services/crawl/crawl_metrics_service.py`

正式收了：

- `CrawlMetricsInput`
- `CrawlMetricsDeps`
- `record_crawl_metrics(...)`

这条 service 现在统一承接：

- 近 24h `posts_hot` 计数
- 活跃社区计数
- `cache_hit_rate` 计算
- `crawl_metrics` 小时级 upsert
- `commit`
- 指标日志

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

`_record_crawl_metrics()` 现在改成薄委托：

1. 组装 `CrawlMetricsInput`
2. 组装 `CrawlMetricsDeps`
3. 调 `record_crawl_metrics(...)`

这意味着：

- `IncrementalCrawler` 不再亲手维护整条 metrics 落地主链
- 后面再改统计口径，不容易继续把抓取入口一起拖重

### 3. 补测试并锁新边界

新增：

- `backend/tests/services/crawl/test_crawl_metrics_service.py`

覆盖：

- 首次写入小时指标
- 既有小时指标上的累加更新
- `valid_posts_24h / total_communities / cache_hit_rate` 口径

继续保留并跑通 wrapper 合同测试：

- `backend/tests/services/crawl/test_incremental_crawler_metrics.py`

同时把新测试夹具拉回当前真实合同：

- `community_cache.community_name` 使用合法的 `r/...`
- `posts_hot.subreddit` 使用合法的 `r/...`
- Decimal 字段断言按当前真实类型处理

## 结果

- `IncrementalCrawler._record_crawl_metrics()` 不再亲手维护整条 metrics 主链
- `crawl metrics` 现在开始有自己的独立真相源
- 后面再改：
  - 24h 有效帖口径
  - 活跃社区口径
  - 小时级累计更新
  - `cache_hit_rate`
  - 指标日志
  不容易再把 `IncrementalCrawler` 一起拖重

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_crawl_metrics_service.py \
  tests/services/crawl/test_incremental_crawler_metrics.py -q
```

结果：

- `6 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/crawl_metrics_service.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_crawl_metrics_service.py
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
- 指标统计和落盘现在开始有独立齿轮
- 数据采集模块继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
