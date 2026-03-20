# Phase 338 - 第三轮继续推进：Seed Crawl Workflow 独立化

## 1. 本轮目标

继续按第三轮“主入口变薄、重活回 workflow、单一真相源更硬”的节奏推进，把旧版 `seed crawl` orchestration 从 `crawler_task.py` 里抽成独立 workflow。

这轮聚焦一件事：

1. 把 `_crawl_seeds_impl()` 里“加载种子社区、构建计划、活跃 tier 过滤、fallback 回退、并发 runner、metrics 汇总”这整段旧版 seed crawl 主链，收成独立 workflow。

## 2. 本轮完成

### 2.1 新增 seed crawl workflow

新增：

- `backend/app/services/crawl/seed_crawl_workflow.py`

正式收了：

- `SeedCrawlWorkflowInput`
- `SeedCrawlWorkflowDeps`
- `SeedCrawlWorkflowResult`
- `run_seed_crawl_workflow(...)`

这条 workflow 统一承接：

- `force_refresh` 下的种子社区加载
- `CrawlPlanBuilder` 计划生成
- `active + crawl_track != none` 过滤
- 允许 tier (`high/medium/low/gold/silver/seed`) 过滤
- 过滤后为空时回退到不过滤种子集
- 并发执行 `run_seed_crawl_with_fallback(...)`
- 失败分支统一收成 `status=failed`
- `record_seed_crawl_metrics(...)` 汇总

### 2.2 收薄 crawler task

修改：

- `backend/app/tasks/crawler_task.py`

新增 seam：

- `_seed_crawl_workflow_deps()`

结果：

- `_crawl_seeds_impl()` 不再自己手写整条旧版 seed crawl orchestration
- 现在只负责：
  1. 取 settings
  2. 构建 cache / reddit client
  3. 组装 `SeedCrawlWorkflowInput`
  4. 调 `run_seed_crawl_workflow(...)`
  5. 返回 `workflow_result.payload`

一个很直观的结果：

- `backend/app/tasks/crawler_task.py`
  - 现在已经压到 `1003` 行

大白话说：

- `crawler_task` 不再自己背“旧版 seed crawl 怎么跑”，开始更像编排入口。

### 2.3 新增 workflow 测试

新增：

- `backend/tests/services/crawl/test_seed_crawl_workflow.py`

覆盖：

1. **allowed tiers 过滤**
   - 只会跑允许 tier 的种子社区

2. **过滤后为空的回退**
   - 如果允许 tier 过滤后空集，会回退到全部 seeds

### 2.4 保持 task 层兼容测试

保留并跑通：

- `backend/tests/tasks/test_crawler_fallback.py`

说明：

- 这次不是把旧 seam 一刀砍掉
- 而是让 task 层通过 `_seed_crawl_workflow_deps()` 注入当前真实边界
- 这样旧 fallback 测试仍然能 patch 到当前真相源，不会因为拆分失去验证能力

## 3. 新增/修改文件

### 新增

- `backend/app/services/crawl/seed_crawl_workflow.py`
- `backend/tests/services/crawl/test_seed_crawl_workflow.py`

### 修改

- `backend/app/tasks/crawler_task.py`

## 4. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_seed_crawl_workflow.py \
  tests/tasks/test_crawler_fallback.py -q
```

结果：

- `4 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/seed_crawl_workflow.py \
  app/tasks/crawler_task.py \
  tests/services/crawl/test_seed_crawl_workflow.py \
  tests/tasks/test_crawler_fallback.py
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

这一轮值钱的地方，不是“又多一个 workflow 文件”，而是：

1. 旧版 `seed crawl` 主链开始有自己的独立齿轮了。
2. `crawler_task` 不再既当入口、又亲手跑完整种子抓取编排。
3. 以后如果再改：
   - 允许 tier 过滤
   - 空集回退
   - 并发 runner
   - metrics 汇总
   就不容易再把 task 壳一起拖重。

大白话说：

- **这轮把“旧版 seed crawl 怎么跑”从 task 壳里真正拆开了。**

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
