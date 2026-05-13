# Phase 311 - 第三轮数据采集模块下一刀：backfill/seed planner workflow 收口

## 背景

第三轮继续打数据采集模块里剩余最重的耦合点。

上一刀已经把：

- `task_outbox dispatcher`
- `execute_target workflow`
- patrol target planner

这几块从 task 壳里拆出来了。

但继续往里看，[crawler_task.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/tasks/crawler_task.py) 里还有两条 planner-only 主链仍然太重：

- `_plan_backfill_bootstrap_impl()`
- `_plan_seed_sampling_impl()`

它们还在 task 层同时背：

- 候选社区查询
- `ensure_crawler_run`
- 构造 crawl plans
- `crawler_run_targets` 入队
- `task_outbox` 入队

大白话：

- task 壳还在一边编排，一边自己做完整 planner workflow

这不符合第三轮继续打磨的目标：

- task 更像薄入口
- planner workflow 有独立齿轮
- planner-only 语义继续变硬

---

## 这一步发现了什么？

### 1. backfill / seed 两条 planner 主链还在各写各的

虽然两条链业务目的不同，但结构其实很像：

1. 查候选社区
2. best-effort 建 `crawler_run`
3. 构造 plans
4. 写 `crawler_run_targets`
5. 写 `task_outbox`
6. 返回 `planned / idle / locked / disabled`

但之前这套流程没有正式 workflow 边界，直接散在 task 壳里。

### 2. `target_planner` 还没真正承接 backfill/seed 这类 target 构造

之前 `target_planner.py` 主要只正式承接了 patrol 这条链。

而 backfill / seed 这两类 target：

- dedupe key 怎么算
- queue 怎么定
- `plan_kind` 怎么配

还没有进入共享 target contract。

### 3. 旧 task 测试还站在“planner 做完整 DB 工作”的旧世界

这次拆 seam 时也顺手照出来：

- task 测试本来就在验证厚 task
- 但第三轮这一步的正确合同已经变成：
  - service 测真 workflow
  - task 只测薄入口和参数委托

---

## 是否需要修复？

需要，而且已经完成。

这次没有：

- 改数据库 schema
- 新增 migration
- 改 planner 业务口径

这次改的是：

- backfill / seed planner workflow 边界
- 共享 target contract
- task 层职责
- 对应测试门禁

---

## 精确修复方法

### 1. 新增独立 planner workflow

新增文件：

- `backend/app/services/crawl/planner_workflow.py`

正式收了：

- `PlannerWorkflowDeps`
- `PlannerWorkflowResult`
- `BackfillBootstrapPlannerInput`
- `SeedSamplingPlannerInput`
- `plan_backfill_bootstrap_workflow(...)`
- `plan_seed_sampling_workflow(...)`

大白话：

- backfill / seed 这两条 planner-only 主链
- 现在开始有自己的正式齿轮了

### 2. 扩展共享 target contract

调整：

- `backend/app/services/crawl/target_planner.py`

这次把共享 target contract 往前推了一步：

- `PlannedCrawlTarget` 增加 `dedupe_key`
- 新增：
  - `build_backfill_bootstrap_target(...)`
  - `build_seed_sampling_targets(...)`

也就是：

- patrol / backfill / seed
- 都开始往同一套 planned target 语言靠

### 3. 把 `crawler_task.py` 收成更薄的 planner 入口

调整：

- `backend/app/tasks/crawler_task.py`

现在：

- `_plan_backfill_bootstrap_impl()`
- `_plan_seed_sampling_impl()`

都只负责：

1. 拿锁
2. 读 env 配置
3. 调 workflow
4. 返回结果

不再自己亲手写完整 planner 主链。

### 4. 测试重新对齐当前真实合同

新增服务层测试：

- `backend/tests/services/crawl/test_planner_workflow.py`

调整 task 层测试：

- `backend/tests/tasks/test_backfill_bootstrap_planner_task.py`
- `backend/tests/tasks/test_seed_sampling_planner_task.py`

这次 task 测试不再假装自己在测完整 DB workflow，而是只测：

- 参数有没有正确下发
- 结果有没有正确透出
- lock 场景是否稳定

---

## 结果

### 结构结果

- backfill / seed planner workflow 开始有独立齿轮
- `target_planner` 不再只服务 patrol
- `crawler_task.py` 继续变薄

### 工程结果

一个很直观的结果是：

- `backend/app/tasks/crawler_task.py`
  - 从上一轮的 `1449` 行
  - 降到了现在的 `1254` 行

一句大白话：

- task 壳更像 task 壳了
- planner workflow 更像独立 workflow 了

### 为什么这一步值钱

这一步真正推进的是：

- 职责更单一
- task / service 边界更清楚
- 同类 planner 语言更统一
- 后面再继续拆 planner-only 链时，不用每次都回到 task 壳里动刀

---

## 验证

### 1. 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/target_planner.py \
  backend/app/services/crawl/planner_workflow.py \
  backend/app/tasks/crawler_task.py \
  backend/tests/services/crawl/test_planner_workflow.py \
  backend/tests/tasks/test_backfill_bootstrap_planner_task.py \
  backend/tests/tasks/test_seed_sampling_planner_task.py
```

结果：

- 通过

### 2. 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_planner_workflow.py \
  tests/tasks/test_backfill_bootstrap_planner_task.py \
  tests/tasks/test_seed_sampling_planner_task.py \
  tests/services/crawl/test_target_planner.py -q
```

结果：

- `8 passed`

### 3. 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 下一步

按第三轮既定节奏，下一刀继续专打剩余最重的耦合点。

当前优先建议回到：

1. `facts / 报告模块`
2. 或 `语义 / 标签模块`

继续沿同一条准则推进：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

一句大白话收口：

- 这刀把数据采集模块里剩下的两条 planner-only 重链也开始拆开了，第三轮节奏还是稳的，可以继续往 95 分以上推进。
