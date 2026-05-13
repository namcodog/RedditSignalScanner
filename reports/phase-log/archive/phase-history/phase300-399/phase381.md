# Phase 381 - 第三轮大包推进：comments_task 入口 wiring / runtime 成组收口

## 1. 发现了什么？

这次收的是 `backend/app/tasks/comments_task.py` 这一整包。

之前这个 task 文件虽然功能都能跑，但它自己背着 8 条入口的运行时 wiring：

- 单帖评论写库
- 单帖评论回填 plan 入队
- 评论语义标注
- full comments 批量回填
- recent full daily
- subreddit snapshot daily
- recent posts label
- high value comments batch

大白话说：

- `comments_task.py` 还是一个大总管
- 入口、plan、reddit client、session、持久化、标注 wiring 全混在一块

这不符合第三轮现在的封板目标：

- task 壳继续变薄
- runtime / support 继续回服务层
- 单一真相源继续做硬

## 2. 是否需要修复？

需要，而且这次已经整包修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 comments task support

新增：

- `backend/app/services/crawl/comments_task_support.py`

正式收走：

- `normalize_configured_subreddits(...)`
- `select_time_filter(...)`
- `build_reddit_client_kwargs(...)`
- `build_backfill_comments_plan(...)`
- `enqueue_backfill_comments_target(...)`
- `DEFAULT_HIGH_VALUE_SUBREDDITS`

也就是说：

- backfill comments 相关 plan / queue / subreddit 配置，不再散在 task 壳里各写一遍

### 3.2 新增 comments task runtime

新增：

- `backend/app/services/crawl/comments_task_runtime.py`

正式收走：

- `run_ingest_post_comments(...)`
- `run_fetch_and_ingest_post_comments(...)`
- `run_label_comments_task(...)`
- `run_backfill_full_comments(...)`
- `run_backfill_recent_full_daily(...)`
- `run_capture_snapshot_daily(...)`
- `run_label_posts_recent_task(...)`
- `run_backfill_high_value_comments(...)`
- `build_comments_task_runtime_deps(...)`

大白话说：

- comments 这 8 条入口现在开始有统一 runtime 真相源了

### 3.3 收薄 comments_task

修改：

- `backend/app/tasks/comments_task.py`

现在这文件主要只保留：

- Celery 入口
- `COMMENTS_BACKFILL_QUEUE`
- `get_settings()`
- `_runtime_deps()`
- 对 runtime 的薄委托

直观结果：

- `backend/app/tasks/comments_task.py`：`582 -> 175`

### 3.4 补测试锁边界

新增：

- `backend/tests/services/crawl/test_comments_task_runtime.py`

覆盖了：

- label comments runtime
- fetch and ingest runtime
- capture snapshot empty-input 早退
- label posts recent runtime

同时继续跑通：

- `backend/tests/services/crawl/test_backfill_comments_workflow.py`
- `backend/tests/services/crawl/test_backfill_comments_executor.py`

## 4. 验证结果

### 4.1 成组定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_comments_task_runtime.py \
  tests/services/crawl/test_backfill_comments_workflow.py \
  tests/services/crawl/test_backfill_comments_executor.py -q
```

结果：

- `13 passed`

### 4.2 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.3 语法自检

```bash
python -m py_compile \
  backend/app/tasks/comments_task.py \
  backend/app/services/crawl/comments_task_support.py \
  backend/app/services/crawl/comments_task_runtime.py \
  backend/tests/services/crawl/test_comments_task_runtime.py
```

结果：

- 通过

## 5. 下一步系统性的计划是什么？

第三轮继续按“大包封板”推进，不再碎跑。

当前剩下最值钱的几包已经很少了：

1. `数据采集模块` 最后一小包清尾
2. `语义 / 标签模块` 最后一包清尾
3. 第三轮总复盘
   正式判断当前系统是否已经稳定站上 `95+`

## 6. 这次执行的价值是什么？达到了什么目的？

这次的价值很直接：

- `comments_task` 不再是一个又抓又排队又标注又回填的大总管
- comments 这条链现在更像：
  - task 壳负责入口
  - support 负责共享 plan / queue / subreddit 规则
  - runtime 负责评论抓取与回填编排

一句大白话总结：

- 这一步不是修一个小点，而是把 `comments_task` 这一整包真正封板了。第三轮现在已经明显进入最后收尾阶段。
