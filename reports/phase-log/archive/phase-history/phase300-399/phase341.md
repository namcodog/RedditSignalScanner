# Phase 341 - 第三轮继续推进：Backfill Posts Workflow 独立化

## 1. 本轮目标

继续按第三轮“主服务变薄、重活回 workflow、单一真相源更硬”的节奏推进，把 `IncrementalCrawler.backfill_posts_window()` 里还缠着的整条回填主链抽成独立 workflow。

这轮聚焦一件事：

1. 把 `backfill_posts_window()` 里“分页抓取、时间窗过滤、cursor 更新、截断判断、水位线推进、最终 payload 汇总”这整段回填主链收成独立 workflow。

## 2. 本轮完成

### 2.1 新增 backfill posts workflow

新增：

- `backend/app/services/crawl/backfill_posts_workflow.py`

正式收了：

- `BackfillPostsWorkflowInput`
- `BackfillPostsWorkflowDeps`
- `BackfillPostsWorkflowResult`
- `execute_backfill_posts_workflow(...)`

这条 workflow 统一承接：

- `since / until` 的时区和合法性校验
- `community_cache` 里已有 `backfill_cursor` 的读取
- 分页抓取 `fetch_subreddit_posts(...)`
- `until / since` 窗口过滤
- `budget_remaining / cursor_remaining / floor_reached / no_more_pages` 收口
- 空集早退 payload
- `_dual_write(...)`
- `backfill_floor / incremental waterline` 推进
- 最终 metrics payload 汇总

大白话说：

- “帖子回填怎么跑”现在开始有自己的正式齿轮了。

### 2.2 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

结果：

- `backfill_posts_window()` 不再自己手写整条回填主链
- 现在只负责：
  1. 校验 `reddit_client`
  2. 组装 `BackfillPostsWorkflowInput`
  3. 注入 `self._dual_write`
  4. 调 `execute_backfill_posts_workflow(...)`
  5. 返回 `workflow_result.payload`

大白话说：

- `IncrementalCrawler` 不再继续既当入口、又亲手跑完整帖子回填。

### 2.3 新增 workflow 测试

新增：

- `backend/tests/services/crawl/test_backfill_posts_workflow.py`

覆盖：

1. **预算打断但没有帖子进窗**
   - 稳定返回 `partial + budget_remaining`

2. **成功路径推进水位线**
   - 正确调用：
     - `dual_write`
     - `update_backfill_floor`
     - `update_incremental_waterline`

### 2.4 保持现有 backfill 回归

保留并跑通：

- `backend/tests/services/crawl/test_backfill_posts_window_empty.py`
- `backend/tests/services/crawl/test_backfill_posts_window_cursor_metrics.py`
- `backend/tests/services/crawl/test_backfill_posts_window_partial_truncation.py`
- `backend/tests/services/crawl/test_backfill_posts_window_fallback.py`

说明：

- 这次不是把 `backfill_posts_window()` 一刀砍掉
- 而是让它变成当前真实边界上的薄委托
- 现有测试继续验证当前合同，不丢兼容

## 3. 新增/修改文件

### 新增

- `backend/app/services/crawl/backfill_posts_workflow.py`
- `backend/tests/services/crawl/test_backfill_posts_workflow.py`

### 修改

- `backend/app/services/crawl/incremental_crawler.py`

## 4. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_backfill_posts_workflow.py \
  tests/services/crawl/test_backfill_posts_window_empty.py \
  tests/services/crawl/test_backfill_posts_window_cursor_metrics.py \
  tests/services/crawl/test_backfill_posts_window_partial_truncation.py \
  tests/services/crawl/test_backfill_posts_window_fallback.py -q
```

结果：

- `7 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/backfill_posts_workflow.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_backfill_posts_workflow.py \
  tests/services/crawl/test_backfill_posts_window_empty.py \
  tests/services/crawl/test_backfill_posts_window_cursor_metrics.py \
  tests/services/crawl/test_backfill_posts_window_partial_truncation.py \
  tests/services/crawl/test_backfill_posts_window_fallback.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- 通过

## 5. 本轮价值

这一轮值钱的地方，不是“又多一个 workflow 文件”，而是：

1. `backfill_posts_window()` 不再继续堆一整条分页 + 过滤 + 水位线推进链
2. 回填帖子这条主链开始只有一个正式真相源
3. 以后如果再改：
   - cursor 规则
   - 时间窗过滤
   - 截断口径
   - 水位线推进
   - payload 汇总
   就不容易再把 `IncrementalCrawler` 一起拖重

大白话说：

- **这轮把“帖子回填怎么跑”从 `IncrementalCrawler` 里真正拆开了。**

## 6. 下一步建议

第三轮继续按当前节奏推进，不换打法。下一刀建议优先继续打：

1. `facts / 报告模块` 剩余 wrapper / seam
2. `数据采集模块` 剩余 side-effect / wrapper
3. `语义 / 标签模块` 剩余 sync / import-export 接缝

原则不变：

- 主服务继续变薄
- task 壳继续变薄
- workflow / service 继续独立
- 单一真相源继续做硬
