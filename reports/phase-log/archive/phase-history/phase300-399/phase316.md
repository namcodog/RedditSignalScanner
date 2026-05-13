# Phase 316 - 第三轮继续打磨：legacy label backfill workflow 拆分

## 1. 发现了什么？

- `llm_label_task.py` 里还残留了一条很重的历史回填链：
  - `_backfill_legacy_labels(...)`
- 它之前还在 task 壳里自己背：
  - 旧 score 数据查询
  - `analysis` 合并与清洗
  - post/comment 两套写库
  - `sync_llm_terms(...)`
  - commit / rollback
  - 最终状态汇总
- 大白话说：
  - **task 壳还在兼任 legacy backfill orchestrator。**

## 2. 是否需要修复？

- 需要，而且已经修完。
- 这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增独立 workflow

新增：

- `backend/app/services/llm/legacy_label_backfill_workflow.py`

正式收了：

- `LegacyLabelBackfillWorkflowInput`
- `LegacyLabelBackfillWorkflowDeps`
- `run_legacy_label_backfill_workflow(...)`

同时把这几件事都收进独立 workflow：

- post legacy rows 查询
- comment legacy rows 查询
- 旧 `analysis` 合并与清洗
- post/comment 持久化
- `sync_llm_terms(...)`
- 状态收口：`completed / degraded / failed`

### 3.2 收薄 task 壳

修改：

- `backend/app/tasks/llm_label_task.py`

现在：

- `_backfill_legacy_labels(...)` 不再自己维护整条回填链
- 改成只组装 input / deps，然后委托给 `run_legacy_label_backfill_workflow(...)`

同时把 `json_sanitize` 依赖从 task 兼容层收回到服务层真相源：

- `app.services.llm.label_batch_support`

### 3.3 测试门禁

新增：

- `backend/tests/services/llm/test_legacy_label_backfill_workflow.py`

覆盖：

- 正常完成时返回 `completed`
- `sync_llm_terms(...)` 失败时返回 `degraded`

补充：

- `backend/tests/tasks/test_llm_label_task.py`

新增 task 委托测试，锁住：

- task 只负责把参数传给 workflow
- 不再自己背 legacy backfill 细节

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_legacy_label_backfill_workflow.py \
  tests/tasks/test_llm_label_task.py \
  tests/services/llm/test_comment_label_workflow.py \
  tests/services/llm/test_label_persistence.py \
  tests/scripts/test_import_client_llm_labels.py \
  tests/services/llm/test_label_contract.py -q
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
  backend/app/services/llm/legacy_label_backfill_workflow.py \
  backend/app/tasks/llm_label_task.py \
  backend/tests/services/llm/test_legacy_label_backfill_workflow.py \
  backend/tests/tasks/test_llm_label_task.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

- 现在在线增量、离线导入、历史回填三条标签链，都开始往“各有独立齿轮”的方向收口。
- `llm_label_task.py` 更像真正的任务入口，不再继续背历史回填主链。
- 这一步继续把第三轮往 `95+` 的目标推进：
  - 职责更清楚
  - task 壳更薄
  - workflow 边界更稳
  - 后面再改 legacy backfill，不会再把在线任务一起拖进来

一句大白话：

- **这刀把语义/标签模块里那条最容易继续缠在 task 壳里的历史回填链，也拆成独立齿轮了。**
