# Phase 383 - 第三轮大包推进：DataCollectionService cache / hot / cold / API fallback 成组封板

## 1. 发现了什么？

这次收的是数据采集模块里还比较重的一条服务主链：

- `backend/app/services/crawl/data_collection.py`

之前 `DataCollectionService.collect_posts(...)` 还自己背着一整条完整 orchestration：

- subreddit 规范化
- cache stale 判断
- Redis 读取
- hot storage fallback
- cold storage fallback
- API fallback
- stale cache fallback
- API 结果统一转 `RedditPost`
- 最终 `CollectionResult` 汇总

大白话说：

- 这个服务入口还是一边当入口，一边亲手跑完整 cache / hot / cold / api fallback 主链

这不符合第三轮现在的封板目标：

- 入口类继续变薄
- 主链继续回到独立 runtime / support
- 单一真相源继续做硬

## 2. 是否需要修复？

需要，而且这次已经整包修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 support 层

新增：

- `backend/app/services/crawl/data_collection_support.py`

正式收走：

- `CollectionResult`
- env 读取
- stale 判断
- subreddit 规范化
- hot/cold record 映射
- timestamp 规范化
- API 结果统一转 `RedditPost`

也就是说：

- cache / hot / cold / api 这条链用到的通用规则，现在开始只有一个正式 support 真相源了

### 3.2 新增 runtime 层

新增：

- `backend/app/services/crawl/data_collection_runtime.py`

正式收走：

- `DataCollectionRuntimeInput`
- `DataCollectionRuntimeDeps`
- `collect_posts_with_fallback(...)`

这条 runtime 统一承接：

- cache -> hot -> cold -> api 的优先级
- stale cache fallback
- API 失败 reason
- 并发 API 抓取
- fake client / 真 client 的 `limit` 调用兼容

### 3.3 收薄入口类

修改：

- `backend/app/services/crawl/data_collection.py`

现在 `DataCollectionService.collect_posts(...)` 已经收成薄入口：

1. 组装 runtime input
2. 组装 runtime deps
3. 调 `collect_posts_with_fallback(...)`

同时保留旧的：

- `_read_int_env`
- `_read_truthy_env`
- `_is_cache_stale`
- `_normalise_subreddits`
- `_map_hot_record`
- `_map_cold_record`
- `_normalise_timestamp`

这些兼容 seam，但它们现在都只是薄委托，不再自己背真正逻辑。

### 3.4 补测试锁边界

新增：

- `backend/tests/services/crawl/test_data_collection_runtime.py`

覆盖了：

- fresh cache 命中时不打 API
- stale cache + API 失败时稳定回退到 stale cache

同时继续跑通：

- `backend/tests/services/crawl/test_data_collection.py`
- `backend/tests/services/crawl/test_incremental_crawl_workflow.py`
- `backend/tests/services/crawl/test_comprehensive_crawl_workflow.py`

## 4. 验证结果

### 4.1 数据采集成组回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_data_collection.py \
  tests/services/crawl/test_data_collection_runtime.py \
  tests/services/crawl/test_incremental_crawl_workflow.py \
  tests/services/crawl/test_comprehensive_crawl_workflow.py -q
```

结果：

- `17 passed`

### 4.2 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.3 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/data_collection.py \
  backend/app/services/crawl/data_collection_support.py \
  backend/app/services/crawl/data_collection_runtime.py \
  backend/tests/services/crawl/test_data_collection_runtime.py
```

结果：

- 通过

## 5. 下一步系统性的计划是什么？

第三轮继续按“大包封板”推进，不再碎跑。

现在已经进入最后收尾阶段，下一步直接做：

1. 第三轮总复盘
2. 正式判断当前系统是否已经稳定站上 `95+`

## 6. 这次执行的价值是什么？达到了什么目的？

这次的价值很直接：

- `DataCollectionService` 不再自己背完整 fallback 主链
- cache / hot / cold / api fallback 现在开始有自己的 runtime 真相源
- 后面再改：
  - stale 口径
  - fallback 优先级
  - API 失败 reason
  - RedditPost 映射
  不容易再把入口类一起拖重

一句大白话总结：

- 这一步不是修一个 helper，而是把 `DataCollectionService` 这一整包真正封板了。
