# Phase 314 - 第三轮继续打磨：评论增量批处理 workflow 拆分

## 1. 这次发现了什么

- `llm_label_task.py` 里的评论增量链虽然已经有：
  - planner
  - label contract
  - persistence
- 但 `_label_comments_batch()` 还在 task 壳里自己背完整批处理 orchestration：
  - 构造 core/lab labeler
  - 长/短样本分流
  - 预算闸门
  - 批量/单条 fallback
  - persist + sync 调用
- 也就是说：
  - **task 壳还在兼任评论批处理 orchestrator。**

## 2. 是否需要修复

- 需要。
- 这次没有改数据库表结构，没有新 migration。
- 改的是语义/标签模块里的：
  - 评论增量批处理边界
  - batch support 真相源位置
  - task 壳厚度

## 3. 精确修复方法

### 3.1 把 batch support 抬成正式公共合同

新增：

- `backend/app/services/llm/label_batch_support.py`

收了原来 task 辅助层里的公共能力：

- `LLMLabelRunStats`
- `process_label_batches(...)`
- `build_post_item(...)`
- `build_comment_item(...)`
- `should_use_long_lab(...)`
- `json_sanitize(...)`

同时把：

- `backend/app/tasks/llm_label_support.py`

收成了**薄兼容壳**，不再自己维护第二份实现。

### 3.2 新增评论增量批处理 workflow

新增：

- `backend/app/services/llm/comment_label_workflow.py`

正式收了：

- `IncrementalCommentLabelWorkflowInput`
- `IncrementalCommentLabelWorkflowDeps`
- `run_incremental_comment_label_workflow(...)`

这条 workflow 现在统一承接：

- API key 检查
- 规则后空候选短路
- core/lab labeler 构造
- 长/短样本分流
- 在线预算闸门
- 批量 / 单条 fallback 执行
- 最终结果汇总

### 3.3 把 llm_label_task 收成薄入口

修改：

- `backend/app/tasks/llm_label_task.py`

变化：

- `_label_comments_batch()` 不再自己手写完整批处理链
- 现在只负责：
  - 读 settings
  - 拿 planner 结果
  - 调 `run_incremental_comment_label_workflow(...)`
  - 返回统一结果

直观结果：

- `backend/app/tasks/llm_label_task.py`
  - 当前行数：`694`

## 4. 测试与门禁

### 新增 workflow 测试

- `backend/tests/services/llm/test_comment_label_workflow.py`

覆盖：

- 规则层全过滤后返回 `no_candidates`
- 预算闸门触发后返回 `degraded`

### task 薄入口测试

- `backend/tests/tasks/test_llm_label_task.py`

新增：

- `test_label_comments_batch_delegates_to_workflow`

锁住：

- `_label_comments_batch()` 现在真的是薄委托入口，不再偷偷把重逻辑长回 task 壳里

### 共享合同回归

- `backend/tests/services/llm/test_label_persistence.py`
- `backend/tests/scripts/test_import_client_llm_labels.py`
- `backend/tests/services/llm/test_label_contract.py`

## 5. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_comment_label_workflow.py \
  tests/tasks/test_llm_label_task.py \
  tests/services/llm/test_label_persistence.py \
  tests/scripts/test_import_client_llm_labels.py \
  tests/services/llm/test_label_contract.py -q
```

结果：

- `14 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/label_batch_support.py \
  backend/app/tasks/llm_label_support.py \
  backend/app/services/llm/comment_label_workflow.py \
  backend/app/tasks/llm_label_task.py \
  backend/tests/services/llm/test_comment_label_workflow.py \
  backend/tests/tasks/test_llm_label_task.py
```

结果：

- 通过

## 6. 这次执行的价值

- 在线评论增量链开始有自己的独立 workflow 了。
- “评论批处理怎么跑”不再继续长在 task 壳里。
- batch support 也不再是 task 私有世界，开始变成正式公共合同。

这一步继续朝当前总整治目标推进：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

## 7. 下一步建议

- 继续优先打：
  - `facts / 报告模块`
  - `数据采集模块`
  - `语义 / 标签模块` 剩余 sync / import-export 边界
- 原则不变：
  - 专打“主服务既编排又亲手干重活”的地方
  - 继续把单一真相源做硬
  - 继续朝 `95+` 的本地产品级稳定状态推进
