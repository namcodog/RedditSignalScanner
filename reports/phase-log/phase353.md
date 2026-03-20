# Phase 353 - 第三轮继续推进：Comprehensive Crawl Workflow 独立化

## 本轮目标

把 `IncrementalCrawler.crawl_community_comprehensive()` 里还缠着的一整条多策略抓取主链，收成独立 workflow。

这轮要解决的不是“能不能抓到帖子”，而是：

- comprehensive crawl 还在入口里自己背：
  - 水位线判断
  - 多策略抓取
  - 水位线后过滤
  - spam 过滤
  - 冷热双写
  - watermark 推进
  - 最终 payload 汇总

大白话说：

- **入口还在一边当入口，一边亲手跑完整 comprehensive crawl。**

## 发现的问题

当前仓库里这条边界还不够干净：

- `backend/app/services/crawl/incremental_crawler.py`
  - `crawl_community_comprehensive(...)`

它和我们前面已经拆出去的：

- `run_incremental_crawl_workflow(...)`
- `execute_backfill_posts_workflow(...)`
- `execute_dual_write(...)`

相比，还是偏重。

这会带来两个问题：

1. `IncrementalCrawler` 继续变胖
2. 后面再改：
   - comprehensive 抓取口径
   - watermark 过滤口径
   - payload 统计口径
   还是要直接碰入口主函数

一句大白话：

- **这条多策略抓取链，已经值回一刀独立 workflow。**

## 修复动作

### 1. 新增 comprehensive crawl workflow

新增：

- `backend/app/services/crawl/comprehensive_crawl_workflow.py`

正式收了：

- `ComprehensiveCrawlWorkflowInput`
- `ComprehensiveCrawlWorkflowDeps`
- `ComprehensiveCrawlWorkflowResult`
- `run_comprehensive_crawl_workflow(...)`

这层现在统一承接：

- 水位线获取
- `fetch_comprehensive_posts(...)`
- 抓取失败 payload
- watermark 过滤
- spam 过滤
- dual write
- watermark 推进
- 最终汇总 payload

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

新增：

- `_comprehensive_crawl_workflow_deps()`

现在 `crawl_community_comprehensive()` 只负责：

1. 校验 `reddit_client`
2. 组装 workflow input
3. 调 `run_comprehensive_crawl_workflow(...)`
4. 补入口日志并返回 payload

也就是说：

- `IncrementalCrawler` 不再继续亲手维护 comprehensive crawl 那整条主链
- 真正干重活的逻辑已经回到独立齿轮里

## 测试与验证

### 新增定向测试

新增：

- `backend/tests/services/crawl/test_comprehensive_crawl_workflow.py`

覆盖：

- 抓取失败返回 error payload
- watermark 过滤后空集早退
- dual write + watermark 更新成功路径

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_comprehensive_crawl_workflow.py -q
```

结果：

- `3 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/comprehensive_crawl_workflow.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_comprehensive_crawl_workflow.py
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

这一步是第三轮里一刀很值钱的“入口减重”：

- `IncrementalCrawler` 又薄了一层
- comprehensive crawl 开始有自己的正式齿轮
- 后面再改：
  - comprehensive 策略
  - watermark 过滤
  - 汇总口径
  不容易再把入口一起拖重

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
