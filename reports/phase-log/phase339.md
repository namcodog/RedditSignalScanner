# Phase 339 - 第三轮继续推进：Seed Archive Workflow 独立化

## 1. 本轮目标

继续按第三轮“主入口变薄、重活回 workflow、单一真相源更硬”的节奏推进，把 `execute_plan.py` 里还内联着的 `seed_top_*` archive 抓取链抽成独立 workflow。

这轮聚焦一件事：

1. 把 `seed_top_year / seed_top_all / seed_controversial_year` 这三类 archive 抓取计划，从 `execute_crawl_plan(...)` 里拆出来，收成独立 workflow。

## 2. 本轮完成

### 2.1 新增 seed archive workflow

新增：

- `backend/app/services/crawl/seed_archive_workflow.py`

正式收了：

- `SeedArchiveWorkflowInput`
- `SeedArchiveWorkflowDeps`
- `SeedArchiveWorkflowResult`
- `execute_seed_archive_workflow(...)`

这条 workflow 统一承接：

- `posts_limit` 上限夹紧
- `cursor_after` 解析
- `seed_top_year / seed_top_all / seed_controversial_year` 的 `sort / time_filter` 收口
- 分页抓取 `fetch_subreddit_posts(...)`
- 空集早退
- `_dual_write(...)` 双写
- `max_seen_created_at / min_seen_created_at` 汇总
- 最终 payload 组装

### 2.2 收薄 execute plan

修改：

- `backend/app/services/crawl/execute_plan.py`

结果：

- `execute_crawl_plan(...)` 不再自己手写 `seed_top_*` archive 抓取主链
- 现在只负责：
  1. 识别 `plan_kind`
  2. 组装 `SeedArchiveWorkflowInput`
  3. 调 `execute_seed_archive_workflow(...)`
  4. 返回 `workflow_result.payload`

大白话说：

- `execute_plan` 不再既当统一执行入口、又亲手跑完整 archive 抓取。

### 2.3 新增 workflow 测试

新增：

- `backend/tests/services/crawl/test_seed_archive_workflow.py`

覆盖：

1. **空集早退**
   - 没抓到帖子时，稳定返回 `completed + total_fetched=0`

2. **seed_top_all 模式**
   - 正确使用 `sort=top + time_filter=all`

3. **seed_controversial_year 模式**
   - 正确使用 `sort=controversial + time_filter=year`
   - 正确汇总 `min/max seen window`

### 2.4 保持 execute_plan 现有 guardrail 测试

保留并跑通：

- `backend/tests/services/crawl/test_execute_crawl_plan_guardrails.py`

说明：

- 这次不是把 `execute_plan` 一刀砍成完全不同的壳
- 而是继续把 archive 特例链收回 workflow，同时保持总入口合同不变

## 3. 新增/修改文件

### 新增

- `backend/app/services/crawl/seed_archive_workflow.py`
- `backend/tests/services/crawl/test_seed_archive_workflow.py`

### 修改

- `backend/app/services/crawl/execute_plan.py`

## 4. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_seed_archive_workflow.py \
  tests/services/crawl/test_execute_crawl_plan_guardrails.py -q
```

结果：

- `4 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/seed_archive_workflow.py \
  app/services/crawl/execute_plan.py \
  tests/services/crawl/test_seed_archive_workflow.py \
  tests/services/crawl/test_execute_crawl_plan_guardrails.py
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

1. `seed_top_*` archive 抓取开始有自己的独立齿轮了。
2. `execute_plan` 不再继续堆 archive 抓取特例。
3. 以后如果再改：
   - 分页抓取
   - archive 时间窗口
   - 双写
   - 汇总 payload
   就不容易再把统一执行入口一起拖重。

大白话说：

- **这轮把“archive seed 怎么跑”从总入口里真正拆开了。**

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
