# Phase 319 - 第三轮继续打磨：post 增量打标签 workflow 拆分

## 1. 发现了什么？

- `llm_label_task.py` 里虽然评论增量链已经拆过一轮，但 `post` 增量打标签这条链还残留着一块很重的 orchestration：
  - `_label_posts_batch(...)`
- 它之前还在 task 壳里自己背：
  - settings / labeler 构造
  - post 候选拉取
  - top comments 拉取
  - core / lab 长短链分流
  - batch / single fallback
  - post 标签持久化编排
- 大白话说：
  - **task 壳还在兼任 post batch orchestrator。**

## 2. 是否需要修复？

- 需要，而且已经修完。
- 这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增独立 workflow

新增：

- `backend/app/services/llm/post_label_workflow.py`

正式收了：

- `IncrementalPostLabelWorkflowInput`
- `IncrementalPostLabelWorkflowDeps`
- `run_incremental_post_label_workflow(...)`

把原来 task 壳里这几件事收回到独立 workflow：

- post 候选读取
- top comments 拼接
- core / lab 长短链分流
- batch / single fallback
- post 标签持久化编排

### 3.2 收薄 task 壳

修改：

- `backend/app/tasks/llm_label_task.py`

现在：

- `_label_posts_batch(...)` 不再自己手写整条增量链
- 改成只组装 input / deps，然后委托给 `run_incremental_post_label_workflow(...)`

同时顺手清掉 task 壳里已经不该继续背的旧 support import：

- `LLMLabelRunStats`
- `build_post_item`
- `process_label_batches`
- `should_use_long_lab`

### 3.3 测试门禁

新增：

- `backend/tests/services/llm/test_post_label_workflow.py`

覆盖：

- batch 结果为空时，single fallback 会把结果标成 `degraded`
- batch 和 single 都失败时，结果会标成 `failed`

同时保留 task 层兼容测试：

- `backend/tests/tasks/test_llm_label_task.py`

锁住：

- task 壳继续保持当前真实合同
- 没有因为拆 workflow 把外层行为带歪

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_post_label_workflow.py \
  tests/tasks/test_llm_label_task.py \
  tests/services/llm/test_comment_label_workflow.py \
  tests/services/llm/test_label_contract.py \
  tests/services/llm/test_label_persistence.py \
  tests/scripts/test_import_client_llm_labels.py -q
```

结果：

- `17 passed`

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/post_label_workflow.py \
  backend/app/tasks/llm_label_task.py \
  backend/tests/services/llm/test_post_label_workflow.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

- 现在 `post` 增量打标签也开始有自己的独立 workflow 了。
- 在线标签链里，`post` 和 `comment` 两条增量链都在往“task 壳变薄、workflow 独立”的方向收口。
- 这一步继续把第三轮往 `95+` 的目标推进：
  - 职责更清楚
  - task 壳更薄
  - 在线标签主链更稳定
  - 后面再改 post 增量策略，不会把整个 `llm_label_task.py` 一起拖回去

一句大白话：

- **这刀把语义/标签模块里那条还缠在 task 壳里的 post 增量打标签主链，也拆成独立齿轮了。**
