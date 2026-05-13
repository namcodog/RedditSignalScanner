# Phase 335 - 第三轮继续推进：Incremental Crawler 主链拆分 + 旧 crawl 失败簇收口

## 1. 本轮目标

在第三轮继续沿着“主入口变薄、重活回 workflow、单一真相源更硬”的节奏推进，并顺手清掉上一轮宽回归里已经明确成簇的一批旧失败，避免第三轮被历史测试漂移反复打断。

本轮聚焦两件事：

1. 把 `IncrementalCrawler.crawl_community_incremental()` 从“大方法亲手背完整增量抓取链”继续收成独立 workflow。
2. 把 `metrics / run_id / search_sharder / backfill_comments_executor` 这一簇旧 crawl 测试失败拉回当前真实合同。

## 2. 本轮完成

### 2.1 新增增量抓取 workflow

新增：

- `backend/app/services/crawl/incremental_crawl_workflow.py`

正式收了：

- `IncrementalCrawlWorkflowInput`
- `IncrementalCrawlWorkflowDeps`
- `IncrementalCrawlWorkflowResult`
- `run_incremental_crawl_workflow(...)`

这条 workflow 统一承接：

- 取水位线
- 调 Reddit 抓帖子
- 空结果 / 失败结果分支
- watermark 后过滤
- spam 过滤
- 冷热双写
- 打分任务触发
- 水位线更新
- crawl_metrics 埋点

### 2.2 收薄 `IncrementalCrawler`

修改：

- `backend/app/services/crawl/incremental_crawler.py`

新增内部 seam：

- `_record_incremental_failure_attempt(...)`
- `_record_incremental_empty_attempt(...)`
- `_dispatch_incremental_score_refresh(...)`
- `_incremental_crawl_workflow_deps()`

结果：

- `crawl_community_incremental()` 不再自己手搓整条增量抓取主链
- 现在只负责：
  1. 记录开始
  2. 组装 workflow input / deps
  3. 调 `run_incremental_crawl_workflow(...)`
  4. 按结果补日志并返回

### 2.3 旧 crawl 失败簇收口

清掉的簇：

- `tests/services/crawl/test_incremental_crawler_metrics.py`
- `tests/services/crawl/test_incremental_crawler_run_id.py`
- `tests/services/crawl/test_search_sharder.py`
- `tests/services/crawl/test_backfill_comments_executor.py`

修复方式：

1. **metrics 测试**
   - 旧测试还在用不符合当前约束的社区名：
     - `r/TestSuccess`
     - `r/TestEmpty`
     - `r/TestFailure`
     - `r/Test{i}`
   - 已统一改成当前真实合同下的规范名：
     - `r/testsuccess`
     - `r/testempty`
     - `r/testfailure`
     - `r/test{i}`

2. **run_id 测试**
   - 当前 `posts_raw` 写入已经依赖社区映射；没有 `community_pool` 会被 quarantine 拦截。
   - 测试已补：
     - 先插入 `community_pool(name='r/test')`
   - 这样 `run_id / community_run_id` 的持久化验证重新回到当前真实世界。

3. **search_sharder 测试**
   - 旧测试还在 import 已漂移的：
     - `scripts.crawl_for_lexicon.JSONLWriter`
   - 已对齐当前真相源：
     - `app.services.crawl.common.JSONLWriter`
   - 同时补成 `stream=True`，因为当前 writer 的 append 合同就是显式流式模式。

4. **backfill_comments_executor 测试**
   - 当前 Dev 库真实合同里：
     - `posts_raw` 需要社区映射
     - `comments` 表实际存在 `post_id NOT NULL`
   - 旧测试没有补这两个前提，所以出现：
     - `NoResultFound`
     - `smart_shallow` 误判成旧帖
     - `num_comments=0` 分支误跑
     - `comments.post_id` 非空约束失败
   - 现已通过测试 helper 拉回当前真实世界：
     - `_ensure_test_community(...)`
     - `_insert_test_post(...)`
   - 并在 “already_up_to_date” 用例里显式补 `comments.post_id`

## 3. 新增/修改文件

### 新增

- `backend/app/services/crawl/incremental_crawl_workflow.py`
- `backend/tests/services/crawl/test_incremental_crawl_workflow.py`

### 修改

- `backend/app/services/crawl/incremental_crawler.py`
- `backend/tests/services/crawl/test_incremental_crawler_metrics.py`
- `backend/tests/services/crawl/test_incremental_crawler_run_id.py`
- `backend/tests/services/crawl/test_search_sharder.py`
- `backend/tests/services/crawl/test_backfill_comments_executor.py`

## 4. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_crawl_workflow.py \
  tests/services/crawl/test_incremental_crawler_metrics.py \
  tests/services/crawl/test_incremental_crawler_run_id.py \
  tests/services/crawl/test_search_sharder.py -q
```

结果：

- `9 passed`

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_backfill_comments_executor.py \
  tests/services/crawl/test_incremental_crawler_metrics.py \
  tests/services/crawl/test_incremental_crawler_run_id.py \
  tests/services/crawl/test_search_sharder.py -q
```

结果：

- `12 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_crawl_workflow.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_crawl_workflow.py \
  tests/services/crawl/test_incremental_crawler_metrics.py \
  tests/services/crawl/test_incremental_crawler_run_id.py \
  tests/services/crawl/test_search_sharder.py \
  tests/services/crawl/test_backfill_comments_executor.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 本轮价值

这一轮值钱的地方不是“又修了几条测试”，而是两件更根上的事：

1. `crawl_community_incremental()` 这条增量抓取主链，又从主类里薄了一层，开始更像独立齿轮。
2. 一串老 crawl 失败，终于被收成“当前真实合同下的稳定测试”，不再继续用旧世界拖第三轮节奏。

大白话说：

- **这轮既推进了结构，也清掉了一串会反复绊脚的旧红灯。**

## 6. 下一步建议

第三轮继续按当前节奏推进，不换打法。下一刀建议优先继续打：

1. `facts / 报告模块`
2. `数据采集模块` 剩余 wrapper / side-effect
3. `语义 / 标签模块` 剩余 sync / import-export 接缝

原则不变：

- 主服务继续变薄
- task 壳继续变薄
- workflow / service 继续独立
- 单一真相源继续做硬
