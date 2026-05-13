# Phase 337 - 第三轮继续推进：Probe Workflow 独立化

## 1. 本轮目标

继续按第三轮“主入口变薄、重活回 workflow、单一真相源更硬”的节奏推进，把 `execute_plan.py` 里最重的 `probe` 分支抽成独立 workflow。

这轮聚焦一件事：

1. 把 `probe` 这条搜索/热榜探针执行链，从“大分支亲手完成抓取、去重、过滤、证据选取、社区发现、warzone 写回”，收成独立 workflow。

## 2. 本轮完成

### 2.1 新增 probe workflow

新增：

- `backend/app/services/crawl/probe_workflow.py`

正式收了：

- `ProbeWorkflowInput`
- `ProbeWorkflowDeps`
- `ProbeWorkflowResult`
- `execute_probe_workflow(...)`

以及 workflow 内部的正式步骤：

- probe 参数与上限收口
- search / hot 两类来源抓取
- 帖子去重、阈值过滤、垃圾过滤
- 证据帖和候选社区选择
- `evidence_posts` 落库
- `community_pool / discovered_communities` 候选社区写入
- warzone best-effort 写回

### 2.2 收薄 execute plan

修改：

- `backend/app/services/crawl/execute_plan.py`

结果：

- `if plan.plan_kind == "probe"` 不再自己手写整条探针执行主链
- 现在只负责：
  1. 组装 `ProbeWorkflowInput`
  2. 组装 `ProbeWorkflowDeps`
  3. 调 `execute_probe_workflow(...)`
  4. 返回 `workflow_result.payload`

一个很直观的结果：

- `backend/app/services/crawl/execute_plan.py`
  - 现在已经压到 `222` 行

大白话说：

- `execute_plan` 不再自己背“探针怎么跑”，开始更像统一编排入口。

### 2.3 新增 workflow 测试

新增：

- `backend/tests/services/crawl/test_probe_workflow.py`

覆盖：

1. **search probe**
   - 能正确写 `evidence_posts`
   - 能正确 upsert `discovered_communities`

2. **hot probe**
   - 命中 caps 时会稳定返回：
     - `status=partial`
     - `reason=caps_reached`
   - 证据帖和候选社区数量符合当前合同

### 2.4 把新测试拉回当前真实合同

这轮新加的 workflow 测试里，顺手把两个容易漂移的点直接对齐了：

1. `RedditPost` 的导入路径
   - 对齐到当前真实模块：
     - `app.services.infrastructure.reddit_client`

2. `hot probe` 的 FK 前提
   - 因为 `evidence_posts.crawl_run_id / target_id` 有真实外键约束
   - 所以测试里显式补：
     - `ensure_crawler_run(...)`
     - `ensure_crawler_run_target(...)`

这样测试验证的是“当前真实系统合同”，不是旧世界里的无依赖假环境。

## 3. 新增/修改文件

### 新增

- `backend/app/services/crawl/probe_workflow.py`
- `backend/tests/services/crawl/test_probe_workflow.py`

### 修改

- `backend/app/services/crawl/execute_plan.py`

## 4. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_probe_workflow.py \
  tests/services/crawl/test_probe_search_executor.py \
  tests/services/crawl/test_probe_hot_executor.py -q
```

结果：

- `5 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/probe_workflow.py \
  app/services/crawl/execute_plan.py \
  tests/services/crawl/test_probe_workflow.py \
  tests/services/crawl/test_probe_search_executor.py \
  tests/services/crawl/test_probe_hot_executor.py
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

这一轮值钱的地方，不是“又拆了一个分支”，而是：

1. `probe` 这条探针执行链，开始有自己的独立齿轮了。
2. `execute_plan` 继续变薄，不再既当总入口、又亲手跑搜索/热榜探针。
3. 以后如果再改：
   - evidence 选择策略
   - hot/search caps
   - candidate 社区写入
   - warzone 写回
   就不容易再把 `execute_plan` 一起拖重。

大白话说：

- **这轮把“探针怎么跑”从总入口里真正拆开了。**

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
