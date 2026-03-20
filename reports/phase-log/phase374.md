# Phase 374 - 第三轮大包推进：crawler_task 运行时 wiring 成组收口

## 1. 发现了什么？

这次不是继续拆一个小 helper，而是直接拿 `crawler_task.py` 这一整组 wiring 开刀。

之前这个文件虽然已经比最早薄了很多，但它还自己背着：

- planner / queue deps 装配
- patrol planner deps 装配
- seed crawl deps 装配
- cache manager / reddit client 构建
- single crawl workflow deps
- 单社区抓取入口
- 旧版 seed crawl 入口
- incremental patrol planner 入口
- backfill bootstrap / seed sampling / low_quality planner 入口
- task outbox dispatcher 入口

大白话说：

- 主 task 已经不跑所有主链了
- 但“这些链怎么接线”还散在 task 文件里

## 2. 是否需要修复？

需要，而且这一大包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增统一运行时层

新增：

- `backend/app/services/crawl/crawler_task_runtime.py`

正式收了：

- `build_planned_target_queue_deps(...)`
- `build_patrol_target_planner_deps(...)`
- `build_planner_workflow_deps(...)`
- `build_patrol_planner_workflow_deps(...)`
- `build_seed_crawl_workflow_deps(...)`
- `build_cache_manager(...)`
- `build_reddit_client(...)`
- `build_single_crawl_workflow_deps(...)`
- `run_single_crawl(...)`
- `run_seed_crawl_task(...)`
- `run_patrol_planner_task(...)`
- `run_backfill_bootstrap_planner(...)`
- `run_seed_sampling_planner(...)`
- `run_low_quality_communities_planner(...)`
- `run_task_outbox_dispatch(...)`
- `load_incremental_seed_profiles(...)`
- `ensure_patrol_parent_run(...)`
- `rank_patrol_seed_profiles(...)`
- `plan_patrol_targets_with_parent_run(...)`

### 3.2 收薄 crawler_task

调整：

- `backend/app/tasks/crawler_task.py`

现在这个文件里的同名函数大多已经收成薄委托：

- 继续保留旧名字，兼容现有 Celery 入口和测试 patch seam
- 真正的 wiring 和 orchestration 已经回到 `crawler_task_runtime.py`

也就是说：

- task 壳继续保留
- 但 task 壳不再自己亲手接整套运行时 wiring

### 3.3 补平兼容测试

新增：

- `backend/tests/services/crawl/test_crawler_task_runtime.py`

并调整：

- `backend/tests/tasks/test_backfill_bootstrap_planner_task.py`
- `backend/tests/tasks/test_seed_sampling_planner_task.py`

让测试回到当前真实合同：

- 不再对比一整坨包含 lambda 的 deps 对象字面相等
- 改成对比真正重要的 session / ensure_run / queue_deps 边界

## 4. 验证结果

### 4.1 成组定向回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_crawler_task_runtime.py \
  tests/tasks/test_crawler_fallback.py \
  tests/tasks/test_comments_preview_toggle.py \
  tests/tasks/test_backfill_bootstrap_planner_task.py \
  tests/tasks/test_seed_sampling_planner_task.py \
  tests/tasks/test_patrol_planner_task.py \
  tests/tasks/test_task_outbox_dispatcher_task.py \
  tests/tasks/test_low_quality_planner_task.py -q
```

结果：

- `21 passed`

### 4.2 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.3 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/crawl/crawler_task_runtime.py \
  backend/app/tasks/crawler_task.py \
  backend/tests/services/crawl/test_crawler_task_runtime.py
```

结果：

- 通过

## 5. 文件体量变化

命令：

```bash
wc -l \
  backend/app/services/crawl/crawler_task_runtime.py \
  backend/app/tasks/crawler_task.py
```

结果：

- `crawler_task_runtime.py`: `668`
- `crawler_task.py`: `772`

最关键的变化是：

- `crawler_task.py` 从之前的 `1002` 行，压到了现在的 `772` 行

这说明这次不是拆了一个小 seam，而是把 task 文件里一整组 wiring 真正抽回运行时层了。

## 6. 当前完成度判断

这一步之后，我的判断是：

- 第三轮完成度：约 `91%-92%`
- 系统整体完成度：约 `94%-95%`

剩下还要收的，已经不多了，主要是：

1. 语义 / 标签模块剩余 sync / import-export 接缝
2. 数据采集模块极少数 wrapper / side-effect 清尾
3. 第三轮总复盘，判断是否已经到 `95+`

## 7. 这次执行的价值是什么？达到了什么目的？

这次最值钱的地方很直接：

- `crawler_task` 里这一整组运行时 wiring 现在开始只有一个正式真相源了
- 后面再改：
  - planner deps
  - patrol deps
  - seed crawl wiring
  - cache/client 构建
  - single crawl 入口
  - task_outbox 派发
  不容易再把 task 壳一起拖重

一句大白话总结：

- 这次把 `crawler_task.py` 这一整包真正压薄了，第三轮已经很接近封板阶段。 
