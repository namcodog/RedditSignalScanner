# Phase 323 - 第三轮：语义/标签模块继续拆离线导入链

## 1. 发现了什么？

- 离线导入脚本 `backend/scripts/import/import_client_llm_labels.py` 之前还在自己背完整导入链：
  - 读 JSONL
  - 分块
  - 拉 post hash
  - 调标签规范化
  - 算分
  - 组装持久化 rows
  - 批量 upsert
- 这会让“离线导入”继续像一条独立实现，而不是语义/标签模块里的统一齿轮。
- 更直接一点说：
  - 在线任务已经越来越薄
  - 离线脚本却还在自己手写整条 workflow

大白话：

- 这条离线导入链还没完全回到统一真相源上。

## 2. 是否需要修复？

- 需要。
- 这是第三轮很典型的一刀：
  - 继续把“脚本既做 CLI，又亲手跑整条业务链”的问题拆开
  - 让脚本只保留入口和护栏
  - 真正导入逻辑回到服务层

## 3. 精确修复方法？

### 3.1 新增独立导入 workflow

- 新增：
  - `backend/app/services/llm/label_import_workflow.py`

正式收了：

- `LabelImportWorkflowInput`
- `LabelImportWorkflowResult`
- `iter_label_jsonl(...)`
- `chunk_label_items(...)`
- `fetch_post_hashes(...)`
- `import_post_label_rows(...)`
- `import_comment_label_rows(...)`
- `import_label_files(...)`

职责固定为：

- 读取导入文件
- 分块导入
- 规范化标签
- 统一算分
- 调共享 persistence upsert

### 3.2 脚本收成薄壳

- 修改：
  - `backend/scripts/import/import_client_llm_labels.py`

现在脚本只负责：

- 解析 CLI 参数
- 做三库护栏
- 调 `import_label_files(...)`
- 打印简单进度

脚本不再自己维护第二套导入实现。

### 3.3 测试分层

- 新增服务层测试：
  - `backend/tests/services/llm/test_label_import_workflow.py`
- 重新定义脚本层测试：
  - `backend/tests/scripts/test_import_client_llm_labels.py`

现在测试分层是：

- 服务层：测 workflow 真逻辑
- 脚本层：测“有没有正确委托给 workflow”

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_label_import_workflow.py \
  tests/scripts/test_import_client_llm_labels.py \
  tests/services/llm/test_label_contract.py \
  tests/services/llm/test_label_persistence.py \
  tests/services/llm/test_comment_label_workflow.py \
  tests/services/llm/test_post_label_workflow.py \
  tests/services/llm/test_legacy_label_backfill_workflow.py \
  tests/tasks/test_llm_label_task.py -q
```

结果：

- `21 passed`

### 语法检查

```bash
python -m py_compile \
  backend/app/services/llm/label_import_workflow.py \
  backend/scripts/import/import_client_llm_labels.py \
  backend/tests/services/llm/test_label_import_workflow.py \
  backend/tests/scripts/test_import_client_llm_labels.py
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

这刀最值钱的地方很直接：

- 离线导入链现在也开始有自己的正式 workflow 了
- 脚本不再自己维护一整套平行业务逻辑
- 在线任务 / 离线导入 / 历史回填，这三条标签链开始更像一套统一体系

当前直观结果：

- `backend/scripts/import/import_client_llm_labels.py`：`79` 行
- `backend/app/services/llm/label_import_workflow.py`：`212` 行

一句大白话总结：

- 第三轮这一步，把离线导入链从“胖脚本”收成了“薄入口 + 正式 workflow”，语义/标签模块又顺了一层。
