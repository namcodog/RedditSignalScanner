# Phase 308 - 第三轮数据采集模块下一刀：planner-only 目标规划/入队收口

## 背景

第三轮继续啃数据采集模块的硬骨头。

上一刀已经把 `execute_target` 主执行链从 task 壳里拆到了独立 workflow。
这一刀继续处理 `crawler_task.py` 里剩下最重的 planner-only 耦合点：

- 巡航 planner：`_plan_patrol_targets()`
- 低质量社区补抓 planner：`_crawl_low_quality_communities_impl()`

这两条链之前都在 task 壳里重复做同一件事：

1. 根据 `CrawlPlanContract` 计算身份证
2. 写 `crawler_run_targets`
3. 写 `task_outbox`
4. 汇总 `inserted/enqueued`

大白话：

- task 壳还在自己“建 target + 入队”
- 这不符合第三轮“职责更单一、边界更清楚”的目标

---

## 这一步发现了什么？

### 1. 剩余最高耦合点已经很明确

`crawler_task.py` 里 patrol/low-quality 这两条 planner-only 链，本质是在重复同一套目标创建/入队逻辑。

这会带来三个问题：

- task 壳继续过重
- planner-only 逻辑没有单一真相源
- 后面在线/离线/新 planner 再扩时，最容易再次各写一遍

### 2. 旧测试口径停留在旧世界

`test_patrol_planner_task.py` 之前把 planner 当成“直接 `send_task`”的逻辑在测。

但当前系统真实合同已经是：

- planner 只写 `crawler_run_targets`
- planner 只写 `task_outbox`
- 真正发 Celery 任务的是 `dispatch_task_outbox`

也就是说：

- 旧测试不是在锁当前真相
- 而是在把系统往旧世界拉

这一步一起把它收回来了。

---

## 是否需要修复？

需要，而且已经完成。

这次没有：

- 改数据库 schema
- 新增 migration
- 改抓取策略本身

这次改的是：

- planner-only 目标规划/入队的服务边界
- task 壳职责
- 测试合同

---

## 精确修复方法

### 1. 新增共享 planner 服务

新增文件：

- `backend/app/services/crawl/target_planner.py`

新增正式边界：

- `PlannedCrawlTarget`
- `PlannedTargetCounts`
- `QueuePlannedTargetsDeps`
- `PatrolTargetPlannerDeps`
- `build_patrol_target(...)`
- `queue_planned_crawl_targets(...)`
- `plan_patrol_targets(...)`

这意味着：

- “怎么从 plan 生成 target 并写入 outbox”
- 现在开始只有一个真相源

### 2. 把 task 壳收成薄入口

调整：

- `backend/app/tasks/crawler_task.py`

新增轻量 deps builder：

- `_planned_target_queue_deps()`
- `_patrol_target_planner_deps()`

收口结果：

- `_plan_patrol_targets()` 现在只负责：
  - best-effort 建父级 run
  - 调用 `plan_patrol_targets(...)`
  - 返回统一结果

- `_crawl_low_quality_communities_impl()` 现在不再自己手搓 target 身份证和 outbox 写入
  - 改成构造 `PlannedCrawlTarget`
  - 再统一调用 `queue_planned_crawl_targets(...)`

### 3. 把测试拉回当前真实合同

新增服务层测试：

- `backend/tests/services/crawl/test_target_planner.py`

覆盖：

- 同一 `crawl_run_id` 下的 idempotent enqueue
- patrol guardrails + waterline 合同

修正 task 层测试：

- `backend/tests/tasks/test_patrol_planner_task.py`

关键调整：

- 不再把 planner 当成“直接 send_task”
- 改成验证：
  - `crawler_run_targets`
  - `task_outbox`
- fixture 改成更隔离的唯一社区名
- recent probe fixture 补父级 `crawler_run`

---

## 结果

### 结构结果

- `crawler_task.py` 从 `1570` 行降到 `1449` 行
- planner-only 目标创建/入队逻辑开始有独立齿轮
- task 壳继续变薄

### 工程结果

这一步把数据采集模块进一步往下面这条准则推进了一层：

- 职责更清楚
- 统一接口协同
- 彼此少牵连
- 链路更顺、更可控

大白话：

- task 入口开始更像“编排壳”
- 目标创建/入队开始更像“独立服务”

---

## 验证

### 1. 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_target_planner.py \
  tests/tasks/test_patrol_planner_task.py \
  tests/tasks/test_crawler_fallback.py \
  tests/tasks/test_task_outbox_dispatcher_task.py -q
```

结果：

- `13 passed`

### 2. 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/target_planner.py \
  backend/app/tasks/crawler_task.py \
  backend/tests/tasks/test_patrol_planner_task.py \
  backend/tests/services/crawl/test_target_planner.py
```

结果：

- 通过

### 3. 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方，不是“多了一个 service 文件”，而是：

- 把数据采集模块里还剩下的一块 planner-only 重逻辑，真正从 task 壳里拆出来了
- 把旧测试也拉回了当前真实合同
- 后面继续打数据采集模块第三轮，不会再围着同一坨“目标创建/入队”反复缠

一句大白话总结：

- 这刀把“planner 只负责下单，不负责直接发任务”这件事彻底钉死了
- 数据采集模块又往产品级稳定状态走近了一步
