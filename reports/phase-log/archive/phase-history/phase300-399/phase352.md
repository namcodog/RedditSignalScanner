# Phase 352 - 第三轮继续推进：Ingest Posts Batch Service 独立化

## 本轮目标

把 `IncrementalCrawler.ingest_posts_batch()` 里还在手搓的一整套冷热双写逻辑，收成独立 service。

这轮要解决的不是“能不能写进去”，而是：

- 同样是帖子批量落地
- 不能 `ingest_posts_batch()` 自己写一套
- `execute_dual_write(...)` 又在别处维护另一套

大白话说：

- **同一件事两只手各写一遍，这种地方最容易后面再漂。**

## 发现的问题

当前仓库里还留着一个很典型的重复重逻辑点：

- `backend/app/services/crawl/incremental_crawler.py`
  - `ingest_posts_batch(...)`

它之前自己背着：

- `dict -> RedditPost` 转换
- 冷库 upsert 循环
- 热缓存 upsert 循环
- flush / commit / rollback
- `posts_latest` 刷新触发

而这些事，本质上和我们前面已经抽出来的：

- `backend/app/services/crawl/incremental_post_persistence_service.py`
  - `execute_dual_write(...)`

是同一件事。

一句大白话：

- **`ingest_posts_batch()` 还是在自己重复写一遍冷热双写。**

## 修复动作

### 1. 新增公共 ingest service

新增：

- `backend/app/services/crawl/ingest_posts_batch_service.py`

正式收了：

- `IngestPostsBatchInput`
- `IngestPostsBatchDeps`
- `IngestPostsBatchResult`
- `build_reddit_posts(...)`
- `ingest_posts_batch(...)`

这层现在统一承接：

- 外部 `dict` 批量转 `RedditPost`
- 空批次早退
- 统一委托给冷热双写执行器

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

现在 `ingest_posts_batch()` 只剩：

1. 组装 workflow input
2. 注入 `self._dual_write`
3. 调新 service
4. 返回兼容 payload

也就是说：

- `IncrementalCrawler` 不再继续亲手维护冷热双写那一坨细节
- 真正干重活的链已经回到独立齿轮里

### 3. 补测试并锁边界

新增：

- `backend/tests/services/crawl/test_ingest_posts_batch_service.py`

覆盖：

- `dict -> RedditPost` 映射
- 空批次早退
- 结果是否真的委托给 `execute_dual_write(...)`

同时保留并跑通：

- `backend/tests/services/crawl/test_incremental_post_persistence_service.py`

## 结果

这轮收完后，数据采集模块里这条边界终于清楚了：

- `IncrementalCrawler` 是入口壳
- `ingest_posts_batch_service` 负责 ingest 批次编排
- `execute_dual_write(...)` 继续做冷热双写真相源

后面再改：

- 批量 ingest payload
- `RedditPost` 映射
- 双写触发规则

不容易再出现：

- 入口一套
- persistence 一套
- 改一处漏一处

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_ingest_posts_batch_service.py \
  tests/services/crawl/test_incremental_post_persistence_service.py -q
```

结果：

- `5 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/ingest_posts_batch_service.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_ingest_posts_batch_service.py
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

这一步是第三轮里一刀很值钱的“重复重逻辑收口”：

- `ingest_posts_batch()` 不再自己维护第二套冷热双写
- 数据采集模块的单一真相源又硬了一层
- `IncrementalCrawler` 继续变薄

这很符合当前第三轮的目标：

- 各模块职责更清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
