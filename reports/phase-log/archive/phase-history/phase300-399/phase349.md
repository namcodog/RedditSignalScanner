# Phase 349 - 第三轮继续推进：Incremental Followup Dispatch Service 独立化

## 本轮目标

继续第三轮结构性打磨，把 `IncrementalCrawler` 里还散着的 3 条 Celery 后置触发链收成一个公共 dispatcher：

- 增量抓取后评分刷新
- 新帖评论回填
- `posts_latest` 刷新

让抓取入口不再继续亲手维护这组 follow-up side-effect。

## 发现的问题

- `backend/app/services/crawl/incremental_crawler.py` 之前还自己背着：
  - `_dispatch_incremental_score_refresh()`
  - `_enqueue_comment_backfill()`
  - `_schedule_posts_latest_refresh()`
- 它们表面不长，但本质上都在做一件同类重活：
  - 直接碰 Celery `send_task`
  - 自己决定 kwargs
  - 自己吞异常并记录日志
- 这会带来两个问题：
  - `IncrementalCrawler` 继续变重
  - 后面再改 follow-up 任务名、参数口径、caps，不容易只改一处

大白话说：

- 增量抓取入口已经拆了很多刀，但“抓完之后还要顺手调哪些任务”这组 side-effect，还没回到独立齿轮里。

## 修复动作

### 1. 新增公共 dispatcher service

新增：

- `backend/app/services/crawl/incremental_followup_dispatch_service.py`

正式收了：

- `IncrementalScoreRefreshInput`
- `CommentBackfillDispatchInput`
- `IncrementalFollowupDispatchDeps`
- `dispatch_incremental_score_refresh(...)`
- `enqueue_comment_backfill(...)`
- `schedule_posts_latest_refresh(...)`

这层现在统一承接：

- `score_new_posts_v1` 的 limit 计算
- `comments.fetch_and_ingest` 的目标排序、caps、kwargs 组装
- `tasks.maintenance.refresh_posts_latest` 调度

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

现在这三段都改成薄委托：

1. 组装 input
2. 组装 `send_task` deps
3. 调新 dispatcher service

一个很直观的结果：

- `backend/app/services/crawl/incremental_crawler.py` 现在是 `874` 行
- 新拆出的 `backend/app/services/crawl/incremental_followup_dispatch_service.py` 是 `94` 行

也就是说：

- 抓取入口又薄了一层
- follow-up side-effect 开始只有一个正式真相源了

### 3. 补测试并锁新边界

新增：

- `backend/tests/services/crawl/test_incremental_followup_dispatch_service.py`

覆盖：

- 评分刷新 limit clamp：`max(200, new_count + 50)`
- 评论回填按 `num_comments` 排序并受 `max_posts` 限制
- `posts_latest` 刷新任务调度

同时保留并验证现有兼容入口：

- `backend/tests/services/crawl/test_incremental_post_persistence_service.py`
- `backend/tests/services/crawl/test_incremental_crawler_dedup.py`
  - 只跑和本轮 follow-up 行为直接相关的两条：
    - `test_comments_backfill_enqueues_for_new_posts`
    - `test_dual_write_triggers_refresh_on_changes`

## 结果

- `IncrementalCrawler` 不再继续亲手维护评分刷新 / 评论回填 / 物化视图刷新这组三条 side-effect
- follow-up 任务调度开始只有一个正式真相源
- 后面再改：
  - task 名
  - kwargs
  - caps
  - 异常日志口径
  不容易再把抓取入口一起拖重

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_followup_dispatch_service.py \
  tests/services/crawl/test_incremental_post_persistence_service.py -q
```

结果：

- `5 passed`

### 兼容入口验证

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_crawler_dedup.py \
  -k 'comments_backfill_enqueues_for_new_posts or dual_write_triggers_refresh_on_changes' -q
```

结果：

- `2 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_followup_dispatch_service.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_followup_dispatch_service.py
```

结果：

- 通过

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 补充说明

我额外跑了更宽的 `test_incremental_crawler_dedup.py`，里面仍有 2 条旧红灯：

- `test_update_detection`
- `test_scd2_creates_new_version_and_expires_previous`

这两条暴露的是旧的版本切换 / current 约束链历史问题，不是这次 `followup dispatch service` 新引入的回归，所以没有混成这轮成果。

## 当前判断

这一步是第三轮里一刀很值钱的结构性收口：

- `IncrementalCrawler` 继续变薄
- follow-up side-effect 开始有自己的独立齿轮
- 数据采集模块继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
