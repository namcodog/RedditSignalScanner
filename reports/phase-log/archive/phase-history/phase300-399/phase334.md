# Phase 334 - 第三轮：增量巡航 planner orchestration 收口

## 1. 发现了什么？

- `crawler_task.py` 里的 `_crawl_seeds_incremental_impl()` 还在背完整增量巡航 planner orchestration：
  - 加载到期社区 / 强制刷新全量社区
  - 过滤主干 tier
  - probe hot fallback
  - 父级 `crawler_run` 建立
  - 自适应排序
  - 最终 `_plan_patrol_targets(...)`
- 大白话说：
  - task 壳还在一边编排，一边自己跑完整巡航下单 workflow。

## 2. 是否需要修复？

- 需要，而且这一步已经修完。
- 这次没有改数据库表结构，没有新增 migration。
- 改的是数据采集模块里“增量巡航 planner”这条 orchestration 边界、task 壳职责和测试门禁。

## 3. 精确修复方法？

### 3.1 新增独立 workflow

新增：

- `backend/app/services/crawl/patrol_planner_workflow.py`

正式收了：

- `PatrolPlannerWorkflowInput`
- `PatrolPlannerWorkflowDeps`
- `PatrolPlannerWorkflowResult`
- `run_patrol_planner_workflow(...)`

这条 workflow 统一承接：

- 载入 seed profiles
- tier 过滤
- idle / planned 判定
- probe fallback 触发
- 父级 run 建立
- 排序
- 最终 patrol target 下单

### 3.2 收薄 `crawler_task.py`

新增 task 侧依赖 seam：

- `_patrol_planner_workflow_deps()`
- `_load_incremental_seed_profiles(...)`
- `_ensure_patrol_parent_run(...)`
- `_rank_patrol_seed_profiles(...)`
- `_plan_patrol_targets_workflow(...)`

然后把：

- `_crawl_seeds_incremental_impl()`

收成薄入口，只负责：

1. 组装 workflow input
2. 调 `run_patrol_planner_workflow(...)`
3. 补最终日志并返回结果

也就是说：

- task 壳不再自己维护整条增量巡航 planner 主链
- 但旧 seam 仍然保留，现有 task 测试可以继续 patch 到当前真实边界

## 4. 当前结果

- `backend/app/services/crawl/patrol_planner_workflow.py`：`105` 行
- `backend/app/tasks/crawler_task.py` 当前：`1046` 行

大白话：

- 增量巡航 planner 这条链，现在开始有自己的独立齿轮了
- task 壳更像入口
- 旧测试依赖的 seam 也没有被粗暴砍掉

## 5. 验证

### 定向 workflow + task 回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_patrol_planner_workflow.py \
  tests/tasks/test_patrol_planner_task.py -q
```

结果：

- `8 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/tasks/crawler_task.py \
  app/services/crawl/patrol_planner_workflow.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 更宽 crawl 回归说明

我额外跑了更宽的数据采集回归：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl \
  tests/tasks/test_patrol_planner_task.py \
  tests/tasks/test_low_quality_planner_task.py \
  tests/tasks/test_backfill_bootstrap_planner_task.py \
  tests/tasks/test_seed_sampling_planner_task.py -q
```

结果里仍有一批旧失败，主要集中在：

- `test_backfill_comments_executor.py`
- `test_incremental_crawler_metrics.py`
- `test_incremental_crawler_run_id.py`
- `test_search_sharder.py`

这些不是本轮引入的新断点，这次不把它们混成本轮成果或回归。

## 6. 下一步系统性的计划是什么？

- 第三轮继续按现在的节奏推进，不换打法。
- 下一刀优先还是专打剩余最重的几块：
  1. `facts / 报告模块`
  2. `数据采集模块`
  3. `语义 / 标签模块`

继续沿同一条线：

- 主服务继续变薄
- task 壳继续变薄
- workflow / service 继续独立
- 单一真相源继续做硬

## 7. 这次执行的价值是什么？达到了什么目的？

- 这次不是修一个小 bug，而是把“增量巡航 planner 怎么跑”真正抽成了独立 workflow。
- 数据采集模块又往你要的状态推进了一步：
  - 各模块职责更清楚
  - 通过统一接口协同
  - 彼此少牵连
  - 整条链路更顺、更可控

一句大白话收口：

- 增量巡航这条链现在不只是能下单了，而是“怎么决定下哪些单”也开始说同一种话了。
