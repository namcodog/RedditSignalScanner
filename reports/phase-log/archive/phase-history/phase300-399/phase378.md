# Phase 378 - 第三轮大包推进：crawl_execute_task helper / wiring / runtime 成组收口

## 1. 发现了什么？

这次收的不是 `execute_target_workflow`，而是它前面的 task 入口整包。

之前 `backend/app/tasks/crawl_execute_task.py` 虽然已经比最早薄很多了，但它还自己背着两大组重逻辑：

- helper 链：
  - target id 解析
  - payload 规范化
  - 社区黑名单状态读取
  - community lock
  - backfill 完成状态收口
  - global rate limiter 构造
- wiring / runtime 链：
  - `ExecuteTargetWorkflowDeps(...)` 整体装配
  - compensation deps 注入
  - trigger deps 注入
  - `_execute_target_impl(...)` 运行时入口

大白话说：

- `execute_target_workflow` 已经是独立齿轮了
- 但 `crawl_execute_task` 还像一个半大的总管

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 support 模块

新增：

- `backend/app/services/crawl/execute_target_task_support.py`

正式收了：

- `parse_uuid(...)`
- `ensure_dict(...)`
- `load_community_blacklist_status(...)`
- `build_global_rate_limiter(...)`
- `needs_community_lock(...)`
- `try_acquire_community_lock(...)`
- `release_community_lock(...)`
- `parse_iso_datetime(...)`
- `backfill_done_months(...)`
- `backfill_posts_min(...)`
- `backfill_comments_min(...)`
- `count_posts_since(...)`
- `count_comments_since(...)`
- `load_backfill_floor(...)`
- `finalize_backfill_status(...)`

### 3.2 新增 runtime 模块

新增：

- `backend/app/services/crawl/execute_target_task_runtime.py`

正式收了：

- `build_execute_target_workflow_deps(...)`
- `run_execute_target_task(...)`

也就是说：

- task 层不再自己手工拼完整 `ExecuteTargetWorkflowDeps`
- compensation / trigger 的 partial 注入，也开始有统一 runtime 真相源

### 3.3 收薄 crawl_execute_task

调整：

- `backend/app/tasks/crawl_execute_task.py`

现在这个文件主要只保留：

- Celery task 入口
- 少量兼容 seam
- session 状态变更那组 wrapper
- 对 support / runtime 的薄委托

一个很直观的结果：

- `crawl_execute_task.py` 从 `498` 行，压到了现在的 `379` 行

当前文件体量：

- `crawl_execute_task.py`: `379`
- `execute_target_task_runtime.py`: `109`
- `execute_target_task_support.py`: `290`

## 4. 兼容性策略

这次没有粗暴砍掉 task 层所有 patch seam，而是保留了几类旧测试还在用的入口：

- `_load_community_blacklist_status(...)`
- `_try_acquire_community_lock(...)`
- `_count_posts_since(...)`
- `_finalize_backfill_status(...)`
- `_execute_target_workflow_deps(...)`

这样做的目的很直接：

- 不让老测试一夜之间全炸
- 但真正的重逻辑已经回到服务层

一句大白话：

- patch 点还留着
- 但真正干重活的不再是 task 壳

## 5. 验证结果

### 5.1 execute_target 成组回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_execute_target_task_runtime.py \
  tests/tasks/test_execute_target_task.py -q
```

结果：

- `21 passed`

### 5.2 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 5.3 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/crawl/execute_target_task_support.py \
  backend/app/services/crawl/execute_target_task_runtime.py \
  backend/app/tasks/crawl_execute_task.py \
  backend/tests/services/crawl/test_execute_target_task_runtime.py
```

结果：

- 通过

## 6. 当前完成度判断

这一步之后，我的判断是：

- 第三轮完成度：约 `93%-94%`
- 系统整体完成度：约 `96%`

剩下真正还值得打的大包，已经不多了，主要是：

1. 数据采集模块最后一小包清尾
2. 语义 / 标签模块最后一包清尾
3. 第三轮总复盘，判断是否正式站稳 `95+`

## 7. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `crawl_execute_task` 不再自己背一整组 helper 和 wiring
- execute target 这条执行链，现在从 task 入口到 workflow 之间，终于有了正式 runtime 真相源
- 后面再改：
  - lock
  - blacklist
  - compensation
  - trigger
  - backfill 完成状态
  不容易再把 task 壳一起拖重

一句大白话总结：

- 这次把 `crawl_execute_task` 这一整包真正抽开了，数据采集模块第三轮已经非常接近封板。
