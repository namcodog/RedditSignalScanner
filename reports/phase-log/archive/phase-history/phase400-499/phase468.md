# Phase 468 - Report Request Workflow 请求链收窄

## 背景

在完成：

- `Canonical Report Assembly` 第一段抽离
- `Report Runtime Factory` 适配器抽离

之后，请求链里还有一块小但典型的混合职责：

- cache hit 判断
- structured 持久化
- cache set 收尾

这些逻辑继续放在 `report_request_workflow.py` 里，会让 request 层一直承担过多杂务。

## 本轮改动

### 1. 新增 request support 模块

- 文件：`backend/app/services/report/report_request_support.py`

当前抽离出的职责：

- `resolve_cached_report_payload(...)`
- `finalize_report_request(...)`

### 2. 收窄 request workflow

- 文件：`backend/app/services/report/report_request_workflow.py`

现在 workflow 更接近：

- 加载上下文
- 校验 analysis
- 调用 assembly
- 返回结果

而不再直接内联 cache 命中判断和收尾持久化逻辑。

### 3. 补齐测试

新增：

- `backend/tests/services/report/test_report_request_support.py`

回归：

- `backend/tests/services/report/test_report_request_workflow.py`

## 验证

通过：

- `cd backend && pytest tests/services/report/test_report_request_support.py tests/services/report/test_report_request_workflow.py -q`
- `cd backend && python -m py_compile app/services/report/report_request_support.py app/services/report/report_request_workflow.py app/services/report/report_runtime.py`

## 结论

这轮之后，请求链边界又收窄了一层。

而且更重要的是：

- `/api/report` 的请求链回归测试通过

说明这次重构仍然没有破坏原来的产品交付合同。

## 下一步

- 继续盘 `report_runtime.py` 的剩余职责
- 准备下一段 runtime 重整
