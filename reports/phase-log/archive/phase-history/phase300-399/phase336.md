# Phase 336 - 第三轮继续推进：Backfill Comments Workflow 独立化

## 1. 本轮目标

继续按第三轮“主入口变薄、重活回 workflow、单一真相源更硬”的节奏推进，把 `backfill_comments` 这条还挂在 `execute_plan` 里的重逻辑抽成独立 workflow。

这轮聚焦一件事：

1. 把 `execute_plan.py` 里的 `backfill_comments` 分支，从“大分支亲手完成上下文解析 + 智能浅抓取配置 + 评论回填 + 可选标签后处理”，收成独立 workflow。

## 2. 本轮完成

### 2.1 新增 backfill comments workflow

新增：

- `backend/app/services/crawl/backfill_comments_workflow.py`

正式收了：

- `BackfillCommentsWorkflowInput`
- `BackfillCommentsWorkflowDeps`
- `BackfillCommentsWorkflowResult`
- `resolve_backfill_post_context(...)`
- `count_existing_backfill_comments(...)`
- `build_smart_shallow_config(...)`
- `execute_backfill_comments_workflow(...)`

这条 workflow 统一承接：

- `target_value` / `meta.subreddit` 基础校验
- 内部 `posts_raw.id` 到 `source_post_id` 的解析
- `posts_raw` 上下文补全：
  - `subreddit`
  - `score`
  - `num_comments`
  - `created_at`
- `no_comments / already_up_to_date` 早退
- `smart_shallow` 的 mode / depth / sort / config 决策
- Reddit comments 抓取
- `persist_comments(...)`
- `label_after_ingest` 下的评论分类与实体提取

### 2.2 收薄 execute plan

修改：

- `backend/app/services/crawl/execute_plan.py`

结果：

- `if plan.plan_kind == "backfill_comments"` 不再自己手写整条回填主链
- 现在只负责：
  1. 组装 `BackfillCommentsWorkflowInput`
  2. 组装 `BackfillCommentsWorkflowDeps`
  3. 调 `execute_backfill_comments_workflow(...)`
  4. 返回 `workflow_result.payload`

大白话说：

- `execute_plan` 不再自己背“评论回填怎么跑”，开始更像编排层。

### 2.3 新增 workflow 测试

新增：

- `backend/tests/services/crawl/test_backfill_comments_workflow.py`

覆盖：

1. **内部 post id 映射**
   - 若错误地传入内部 `posts_raw.id`，workflow 会先映射回真正的 `source_post_id`

2. **无评论早退**
   - `num_comments <= 0` 时稳定返回：
     - `status=completed`
     - `processed=0`
     - `reason=no_comments`

3. **旧帖 smart_shallow 配置**
   - 老帖子会收成：
     - `mode=smart_shallow`
     - `smart_top_limit=40`
     - `smart_new_limit=0`

## 3. 新增/修改文件

### 新增

- `backend/app/services/crawl/backfill_comments_workflow.py`
- `backend/tests/services/crawl/test_backfill_comments_workflow.py`

### 修改

- `backend/app/services/crawl/execute_plan.py`

## 4. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_backfill_comments_workflow.py \
  tests/services/crawl/test_backfill_comments_executor.py -q
```

结果：

- `9 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/backfill_comments_workflow.py \
  app/services/crawl/execute_plan.py \
  tests/services/crawl/test_backfill_comments_workflow.py \
  tests/services/crawl/test_backfill_comments_executor.py
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

这一轮值钱的地方，不是“把一个长分支换了个文件”，而是：

1. `backfill_comments` 这条评论回填主链，开始有自己的独立齿轮了。
2. `execute_plan` 不再既当分发器、又亲手跑完整回填逻辑。
3. 后面如果再改：
   - internal post id 映射
   - smart shallow 配置
   - label-after-ingest
   就不容易再把 `execute_plan` 一起拖重。

大白话说：

- **这轮把“评论回填怎么跑”从总入口里真正拆开了。**

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
