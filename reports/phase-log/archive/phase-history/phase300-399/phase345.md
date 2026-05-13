# Phase 345 - 第三轮继续推进：Incremental Hot Cache Service 独立化

## 本轮目标

继续第三轮结构性打磨，在冷库 upsert 主链已经拆出去之后，把 `IncrementalCrawler._upsert_to_hot_cache()` 也拆成独立 service，让冷热双写两半都回到独立齿轮里。

## 发现的问题

- `backend/app/services/crawl/incremental_crawler.py` 里的 `_upsert_to_hot_cache()` 之前还在自己背：
  - 作者保证
  - TTL 计算
  - `PostHot` upsert
  - 无唯一约束时的 fallback 查询 + 覆盖更新
- 这让 `IncrementalCrawler` 继续同时承担：
  - 抓取入口
  - 冷库落地
  - 热缓存落地
  - 双写编排

大白话说：

- 冷库这半边已经拆了，但热缓存这半边还挂在入口类里，没有收干净。

## 修复动作

### 1. 新增独立 service

新增：

- `backend/app/services/crawl/incremental_hot_cache_service.py`

正式收了：

- `HotCacheUpsertInput`
- `HotCacheUpsertDeps`
- `upsert_post_to_hot_cache(...)`

这条 service 现在统一承接：

- 作者保证
- TTL 计算
- `PostHot` upsert
- 无唯一约束时的 fallback 查询 + 覆盖更新

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

`_upsert_to_hot_cache()` 现在改成薄委托：

1. 组装 `HotCacheUpsertInput`
2. 组装 `HotCacheUpsertDeps`
3. 调 `upsert_post_to_hot_cache(...)`

这意味着：

- 冷库主链和热缓存主链现在都已经从 `IncrementalCrawler` 里拆开了
- `dual_write` 这组齿轮的边界更完整了

### 3. 补测试并锁新边界

新增：

- `backend/tests/services/crawl/test_incremental_hot_cache_service.py`

覆盖：

- `author_id / author_name` 会稳定落到 `PostHot`
- `subreddit` 会保持 canonical key
- `extra_data.permalink` 会稳定写入

继续保留并跑通现有 wrapper 合同测试：

- `backend/tests/services/crawl/test_incremental_crawler_run_id.py`
- `backend/tests/services/crawl/test_incremental_crawler_dedup.py::TestIncrementalCrawlerDedup::test_hot_cache_persists_author_metadata`

## 结果

- `IncrementalCrawler._upsert_to_hot_cache()` 不再亲手维护整条热缓存 upsert 主链
- 冷库 + 热缓存这两半现在都开始有自己的独立真相源
- 后面再改：
  - TTL 口径
  - `PostHot` upsert
  - fallback 查询更新
  - author / metadata 写入
  不容易再把 `IncrementalCrawler` 一起拖重

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_cold_storage_service.py \
  tests/services/crawl/test_incremental_hot_cache_service.py \
  tests/services/crawl/test_incremental_crawler_run_id.py \
  tests/services/crawl/test_incremental_crawler_dedup.py::TestIncrementalCrawlerDedup::test_hot_cache_persists_author_metadata -q
```

结果：

- `5 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_cold_storage_service.py \
  app/services/crawl/incremental_hot_cache_service.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_cold_storage_service.py \
  tests/services/crawl/test_incremental_hot_cache_service.py
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
- 冷库 + 热缓存两半现在都开始有独立齿轮
- 数据采集模块继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
