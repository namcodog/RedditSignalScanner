# Phase 362 - IncrementalCrawler workflow deps 装配链抽离

## 1. 发现了什么？

这一步第三轮继续打的是数据采集模块里还留在入口类上的 deps 装配链：

- `backend/app/services/crawl/incremental_crawler.py`

虽然前面已经把：

- incremental crawl workflow
- comprehensive crawl workflow
- dual write
- cold/hot storage
- metrics

都拆成独立齿轮了，但 `IncrementalCrawler` 还在自己维护两段闭包装配：

- `_incremental_crawl_workflow_deps()`
- `_comprehensive_crawl_workflow_deps()`

里面还直接背着：

- `reddit_client` 校验
- fetch 闭包
- watermark 更新闭包
- dual_write / spam filter / metrics wiring

大白话说：

- 入口已经薄了不少
- 但 workflow 依赖怎么接起来，还没有自己的正式真相源

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 deps factory

新增：

- `backend/app/services/crawl/incremental_crawler_deps_factory.py`

正式收了：

- `IncrementalCrawlerDepsFactoryInput`
- `build_incremental_crawl_workflow_deps(...)`
- `build_comprehensive_crawl_workflow_deps(...)`

现在这块统一负责：

- `reddit_client` 存在性校验
- incremental fetch 闭包
- comprehensive fetch 闭包
- comprehensive watermark update 包装
- `dual_write / spam filter / metrics / watermark` 这套 wiring

### 3.2 收薄 IncrementalCrawler

更新：

- `backend/app/services/crawl/incremental_crawler.py`

现在：

- `_incremental_crawl_workflow_deps()`
- `_comprehensive_crawl_workflow_deps()`

都不再自己维护一大段闭包，而是只负责：

1. 组装 `IncrementalCrawlerDepsFactoryInput`
2. 调 factory
3. 返回 deps

也就是说：

- 入口类又薄了一层
- workflow wiring 开始也有自己的正式齿轮了

### 3.3 新增定向测试

新增：

- `backend/tests/services/crawl/test_incremental_crawler_deps_factory.py`

锁住三件事：

- incremental fetch 确实走 `reddit_client.fetch_subreddit_posts(...)`
- comprehensive watermark update 的包装参数不漂
- 没有 `reddit_client` 时，factory 生成的 deps 会稳定抛出当前真实错误

同时继续保留并跑通：

- `backend/tests/services/crawl/test_incremental_crawl_workflow.py`
- `backend/tests/services/crawl/test_comprehensive_crawl_workflow.py`

## 4. 测试与验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_crawler_deps_factory.py \
  tests/services/crawl/test_incremental_crawl_workflow.py \
  tests/services/crawl/test_comprehensive_crawl_workflow.py -q
```

结果：

- `9 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_crawler_deps_factory.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_crawler_deps_factory.py
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

- `IncrementalCrawler` 里剩下的 workflow deps 装配链，现在开始也有自己的独立齿轮了
- 后面再改：
  - fetch 闭包
  - watermark wiring
  - spam filter / dual write / metrics 接线
  就不容易再把入口类一起拖重

一句大白话：

- 这一步不是修小毛病，而是把数据采集模块里还留在入口类上的一大段 workflow 装配链正式抽开了。
