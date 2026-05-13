# Phase 469 - Report Runtime 输入装配抽离

## 背景

在完成：

- `Canonical Report Assembly` 第一段
- `Report Runtime Factory` 适配器抽离
- `Report Request Workflow` 请求链收窄

之后，`report_runtime.py` 里还残留着一类典型混合职责：

- 读 settings
- 选默认依赖
- 组装 factory input

这些逻辑继续留在 runtime 门面里，会让这一层始终既像门面，又像配置拼装器。

## 本轮改动

### 1. 新增 runtime inputs 模块

- 文件：`backend/app/services/report/report_runtime_inputs.py`

当前抽离出的函数：

- `build_runtime_assembly_factory_input(...)`
- `build_runtime_request_factory_input(...)`

### 2. 收窄 runtime 门面

- 文件：`backend/app/services/report/report_runtime.py`

现在 `report_runtime.py` 更接近：

- 暴露运行时能力
- 调用 inputs 模块生成 factory input
- 再交给 factory 层

而不再自己展开大段配置拼装细节。

### 3. 补齐测试

新增：

- `backend/tests/services/report/test_report_runtime_inputs.py`

并联回归：

- `backend/tests/services/report/test_report_assembly_deps_factory.py`
- `backend/tests/services/report/test_report_request_deps_factory.py`
- `backend/tests/services/report/test_report_request_workflow.py`

## 验证

通过：

- `cd backend && pytest tests/services/report/test_report_runtime_inputs.py tests/services/report/test_report_assembly_deps_factory.py tests/services/report/test_report_request_deps_factory.py tests/services/report/test_report_request_workflow.py -q`
- `cd backend && python -m py_compile app/services/report/report_runtime_inputs.py app/services/report/report_runtime.py app/services/report/report_runtime_factory.py`

## 结论

这轮之后，`report_runtime.py` 又瘦了一层。

而且更重要的是：

- runtime 相关回归测试继续通过

说明这次拆分仍然没有破坏原来的 `Full A` 对外交付合同。

## 下一步

- 继续盘 `report_runtime.py` 剩余职责
- 准备下一段 runtime 重整
