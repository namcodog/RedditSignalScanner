# Phase 348 - 第三轮继续推进：Crawl Plan Dispatcher 独立化

## 本轮目标

继续第三轮结构性打磨，把 `execute_plan` 里还内联着的多分支分发逻辑拆成独立 dispatcher：

- `patrol`
- `backfill_posts`
- `seed_top_*`
- `probe`
- `backfill_comments`

让总入口不再继续一边做 guardrail，一边亲手把不同 `plan_kind` 的执行分支全接住。

## 发现的问题

- `backend/app/services/crawl/execute_plan.py` 之前虽然已经拆掉了不少 workflow，但 `execute_crawl_plan(...)` 还在自己背：
  - `plan_kind` 分支判断
  - `crawler_factory` 初始化
  - `backfill_posts` 额外 window 校验
  - `seed archive / probe / backfill_comments` 三类 workflow 分发
- 这会带来两个问题：
  - 总入口继续变重
  - 后面再改任一 `plan_kind` 分支，都容易把 `execute_plan` 一起拖重

大白话说：

- `execute_plan` 还像一个“大总管”，没有真正退回成薄编排层。

## 修复动作

### 1. 新增独立 dispatcher

新增：

- `backend/app/services/crawl/crawl_plan_dispatcher.py`

正式收了：

- `CrawlPlanDispatchInput`
- `CrawlPlanDispatchDeps`
- `dispatch_crawl_plan(...)`

这层现在统一承接：

- `patrol` 的 limit / `time_filter` clamp
- `backfill_posts` 的 crawler 调用
- `seed_top_*` archive workflow 分发
- `probe` workflow 分发
- `backfill_comments` workflow 分发

### 2. 收薄 execute_plan

修改：

- `backend/app/services/crawl/execute_plan.py`

现在 `execute_crawl_plan(...)` 只负责：

1. guardrail 和 plan 合法性前置检查
2. 组装 `CrawlPlanDispatchInput`
3. 调 `dispatch_crawl_plan(...)`
4. 返回 payload

一个很直观的结果：

- `backend/app/services/crawl/execute_plan.py` 现在是 `85` 行
- 新拆出的 `backend/app/services/crawl/crawl_plan_dispatcher.py` 是 `159` 行

也就是说：

- 总入口已经明显退回到薄编排层
- 真正的多分支执行分发，开始有自己的独立齿轮了

### 3. 把新测试拉回当前真实合同

新增测试：

- `backend/tests/services/crawl/test_crawl_plan_dispatcher.py`

这轮顺手修了两个新测试自己的旧心智：

- `backfill_posts` 现在在 `CrawlPlanContract(...)` 构造期就要求 `window.since / window.until`
  - 所以 `raises` 要放在 model 构造处，而不是 dispatcher 调用处
- `probe` 现在在 `CrawlPlanContract(...)` 构造期就要求：
  - `meta.source in {'search','hot'}`
  - `search` 场景对应 `target_type='query'`

这两处修完后，新测试重新回到当前真实合同，不再拿旧世界心智误判 dispatcher。

## 结果

- `execute_crawl_plan(...)` 不再继续亲手维护多分支执行分发
- `crawl plan` 的执行分发，开始只有一个正式真相源
- 后面再改任一 `plan_kind` 分支，不容易再把总入口一起拖重

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_crawl_plan_dispatcher.py \
  tests/services/crawl/test_execute_crawl_plan_guardrails.py \
  tests/services/crawl/test_probe_search_executor.py \
  tests/services/crawl/test_probe_hot_executor.py \
  tests/services/crawl/test_backfill_comments_executor.py -q
```

结果：

- `13 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/crawl_plan_dispatcher.py \
  app/services/crawl/execute_plan.py \
  tests/services/crawl/test_crawl_plan_dispatcher.py
```

结果：

- 通过

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 当前判断

这一步是第三轮里一刀很值钱的结构性收口：

- `execute_plan` 更像真正的编排层
- `crawl plan` 多分支分发开始有独立齿轮
- 数据采集模块继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
