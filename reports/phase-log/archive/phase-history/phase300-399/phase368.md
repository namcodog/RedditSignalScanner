# Phase 368 - 语义/标签模块入口 wiring 成组收口

## 1. 发现了什么？

这一步第三轮按“大包推进”打的是语义/标签模块里 `llm_label_task` 还留着的一整组入口 wiring：

- `backend/app/tasks/llm_label_task.py`

前面虽然已经把：

- post/comment workflow
- legacy backfill workflow
- label contract / persistence / planner

都拆成独立齿轮了，但 task 壳里还自己背着一整组入口拼装：

- 配置读取
- post workflow input/deps 组装
- comment workflow input/deps 组装
- legacy backfill workflow input/deps 组装
- SessionFactory / LLMLabeler / persistence / sync 这一整套依赖 wiring

大白话说：

- `llm_label_task` 已经比以前薄了
- 但它还没有收成真正的“任务壳”

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增统一 runtime 层

新增：

- `backend/app/services/llm/llm_label_task_runtime.py`

正式收了：

- `LLMLabelTaskRuntimeConfig`
- `LLMLabelTaskRuntimeDeps`
- `run_label_posts_task(...)`
- `run_label_comments_task(...)`
- `run_backfill_legacy_labels_task(...)`

现在这块统一负责：

- 三条入口的 workflow input 组装
- 三条入口的 deps 组装
- 统一把 settings / session / labeler / persistence / sync / planner 接起来

### 3.2 收薄 llm_label_task

更新：

- `backend/app/tasks/llm_label_task.py`

这次保留了少量 patch seam：

- `_fetch_post_candidates(...)`
- `_fetch_top_comments(...)`

但把真正重的那部分都收走了：

- `_label_posts_batch(...)`
- `_label_comments_batch(...)`
- `_backfill_legacy_labels(...)`

现在这三条都只做一件事：

- 组装 runtime deps
- 调 runtime runner

也就是说：

- task 壳不再自己维护三套 workflow wiring
- 但现有测试里依赖的 patch seam 还保着，不会一下子炸掉

### 3.3 新增定向测试

新增：

- `backend/tests/services/llm/test_llm_label_task_runtime.py`

锁住三件事：

- post 入口会正确构建 workflow input/deps
- comment 入口会正确构建 plan 和 budget cap
- legacy backfill 入口会正确透传 workflow input/deps

同时继续保留并跑通：

- `backend/tests/services/llm/test_post_label_workflow.py`
- `backend/tests/services/llm/test_comment_label_workflow.py`
- `backend/tests/services/llm/test_legacy_label_backfill_workflow.py`
- `backend/tests/tasks/test_llm_label_task.py`
- `backend/tests/scripts/test_export_llm_label_candidates.py`

## 4. 测试与验证

### 成组定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_llm_label_task_runtime.py \
  tests/services/llm/test_post_label_workflow.py \
  tests/services/llm/test_comment_label_workflow.py \
  tests/services/llm/test_legacy_label_backfill_workflow.py \
  tests/tasks/test_llm_label_task.py \
  tests/scripts/test_export_llm_label_candidates.py -q
```

结果：

- `19 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/llm_label_task_runtime.py \
  backend/app/tasks/llm_label_task.py \
  backend/tests/services/llm/test_llm_label_task_runtime.py
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

- `llm_label_task` 里三条入口的 wiring，现在开始只有一个正式真相源了
- 后面再改：
  - settings
  - workflow input
  - workflow deps
  - persistence / sync 注入
  不容易再三条入口一起漂

一句大白话：

- 这一步不是修一个 helper，而是把语义/标签模块里“任务入口怎么接三条链”这一整包正式抽回运行时服务层了，`llm_label_task` 开始更像真正的任务壳了。
