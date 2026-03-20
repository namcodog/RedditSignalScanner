# Phase 375 - 第三轮大包推进：标签导入/导出 CLI wiring 成组收口

## 1. 发现了什么？

这次收的不是单个脚本，而是整条离线标签 IO 链。

之前这两条 CLI 还各自背着一套 wiring：

- `backend/scripts/report/export_llm_label_candidates.py`
- `backend/scripts/import/import_client_llm_labels.py`

它们自己处理：

- 参数校验
- Dev/Gold 库守卫
- SessionFactory 组装
- export/import service 调用
- 进度打印

大白话说：

- 在线标签链已经越来越像正式模块
- 但离线 CLI 这条链还没收成单一真相源

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增统一 runtime 层

新增：

- `backend/app/services/llm/label_io_runtime.py`

正式收了：

- `LabelExportCliInput`
- `LabelImportCliInput`
- `ensure_non_gold_database(...)`
- `run_label_export_cli(...)`
- `run_label_import_cli(...)`

### 3.2 收薄两个 CLI 脚本

调整：

- `backend/scripts/report/export_llm_label_candidates.py`
- `backend/scripts/import/import_client_llm_labels.py`

现在两条 CLI 都只负责：

- 读参数
- 组装 input
- 调统一 runtime

也就是说：

- Gold/Dev guardrail 开始只有一个正式真相源
- export/import 的命令行 wiring 也开始说同一种话

### 3.3 补测试锁边界

新增：

- `backend/tests/services/llm/test_label_io_runtime.py`

并调整：

- `backend/tests/scripts/test_import_client_llm_labels.py`
- `backend/tests/scripts/test_export_llm_label_candidates.py`

## 4. 验证结果

### 4.1 成组定向回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_label_io_runtime.py \
  tests/scripts/test_import_client_llm_labels.py \
  tests/scripts/test_export_llm_label_candidates.py \
  tests/services/llm/test_label_import_workflow.py \
  tests/services/llm/test_label_export_service.py -q
```

结果：

- `11 passed`

### 4.2 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/llm/label_io_runtime.py \
  backend/scripts/report/export_llm_label_candidates.py \
  backend/scripts/import/import_client_llm_labels.py \
  backend/tests/services/llm/test_label_io_runtime.py \
  backend/tests/scripts/test_import_client_llm_labels.py \
  backend/tests/scripts/test_export_llm_label_candidates.py
```

结果：

- 通过

## 5. 当前完成度判断

这一步之后，我的判断是：

- 第三轮完成度：约 `93%-94%`
- 系统整体完成度：约 `95%`

## 6. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- 离线标签导出/导入这条 CLI 链，现在开始只有一个正式 runtime 真相源了
- 后面再改：
  - Gold/Dev 库守卫
  - 进度打印
  - SessionFactory 装配
  - export/import 参数口径
  不容易再让两个脚本各写各的

一句大白话总结：

- 这次把离线标签 IO 这一整包真正收成一套统一入口了。
