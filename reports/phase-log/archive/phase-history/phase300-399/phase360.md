# Phase 360 - crawl_plan_dispatcher 剩余内联分支拆分

## 1. 发现了什么？

这一步第三轮继续打的是数据采集模块里还偏重的分发器：

- `backend/app/services/crawl/crawl_plan_dispatcher.py`

虽然前面已经把 `seed_archive / probe / backfill_comments` 拆成独立 workflow 了，但 `patrol` 和 `backfill_posts` 还在 dispatcher 里内联执行：

- 自己解析和兜底 plan 参数
- 自己创建 `IncrementalCrawler`
- 自己直接调 crawler 方法

大白话说：

- dispatcher 还不是真正的分发器
- 还在自己亲手跑两条主链

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 patrol workflow

新增：

- `backend/app/services/crawl/patrol_workflow.py`

正式收了：

- `PatrolWorkflowInput`
- `PatrolWorkflowDeps`
- `PatrolWorkflowResult`
- `execute_patrol_workflow(...)`

现在 `patrol` 这条链里的：

- `posts_limit` clamp
- `time_filter` 兜底
- `hot_cache_ttl_hours` 读取
- `IncrementalCrawler` 实例化
- `crawl_community_incremental(...)`

都回到了独立 workflow 里。

### 3.2 新增 backfill_posts plan workflow

新增：

- `backend/app/services/crawl/backfill_posts_plan_workflow.py`

正式收了：

- `BackfillPostsPlanWorkflowInput`
- `BackfillPostsPlanWorkflowDeps`
- `BackfillPostsPlanWorkflowResult`
- `execute_backfill_posts_plan_workflow(...)`

现在 `backfill_posts` 分支里的：

- window 必填校验
- `cursor_after` 规范化
- `sort` 兜底
- `IncrementalCrawler` 实例化
- `backfill_posts_window(...)`

也回到了独立 workflow 里。

### 3.3 收薄 dispatcher 和 execute_plan

更新：

- `backend/app/services/crawl/crawl_plan_dispatcher.py`
- `backend/app/services/crawl/execute_plan.py`

现在 `dispatch_crawl_plan(...)` 对 `patrol / backfill_posts` 的处理方式，已经和前面拆出去的几类 plan 一致：

1. 组装 workflow input
2. 调 execute_xxx_workflow
3. 返回 workflow payload

也就是说：

- dispatcher 更像真正的分发器了
- `execute_plan` 更像依赖装配壳了

## 4. 测试与验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_patrol_workflow.py \
  tests/services/crawl/test_backfill_posts_plan_workflow.py \
  tests/services/crawl/test_crawl_plan_dispatcher.py -q
```

结果：

- `6 passed`

### guardrail 回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_execute_crawl_plan_guardrails.py -q
```

结果：

- `1 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/patrol_workflow.py \
  app/services/crawl/backfill_posts_plan_workflow.py \
  app/services/crawl/crawl_plan_dispatcher.py \
  app/services/crawl/execute_plan.py \
  tests/services/crawl/test_patrol_workflow.py \
  tests/services/crawl/test_backfill_posts_plan_workflow.py \
  tests/services/crawl/test_crawl_plan_dispatcher.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `crawl_plan_dispatcher` 里最后两条还内联的执行主链，开始也有自己的独立齿轮了
- `dispatch_crawl_plan(...)` 更像真正的分发器
- 后面再改 `patrol / backfill_posts`，不容易把 dispatcher 一起拖重

一句大白话：

- 这一步不是修小毛病，而是把数据采集模块里“分发器还亲手跑主链”这个剩余重口子收掉了。
