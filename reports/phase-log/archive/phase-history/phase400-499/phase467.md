# Phase 467 - Report Runtime Factory 适配器抽离

## 背景

在完成：

- `Canonical Report Assembly` 第一段抽离

之后，report 侧还有一个典型的臃肿点：

- `report_runtime_factory.py`

这个文件里塞了很多闭包适配器：

- market report
- controlled summary
- inline structured
- narrative
- request context
- assemble payload

如果不继续拆，这一层会越来越像“测试还能跑、但谁都不想碰”的黑盒。

## 本轮改动

### 1. 新增 adapters 模块

- 文件：`backend/app/services/report/report_factory_adapters.py`

当前抽离出的适配器构建包括：

- `make_market_report_builder(...)`
- `make_market_enhancements_builder(...)`
- `make_controlled_summary_renderer(...)`
- `make_controlled_markdown_builder(...)`
- `make_inline_structured_report_builder(...)`
- `make_narrative_report_builder(...)`
- `make_request_context_loader(...)`
- `make_report_payload_assembler(...)`

### 2. 收窄 runtime factory

- 文件：`backend/app/services/report/report_runtime_factory.py`

现在 `report_runtime_factory.py` 开始回到：

- 读取配置
- 组合适配器
- 返回工厂 deps

而不再继续自己内联一大堆闭包逻辑。

### 3. 保留原有测试接缝

这轮特意没有破坏：

- `report_runtime_factory` 上原来的 monkeypatch 接缝

这样做的目的很明确：

- 可以继续拆内部边界
- 但不把已有测试和依赖注入模式一起打坏

## 验证

通过：

- `cd backend && pytest tests/services/report/test_report_assembly_deps_factory.py tests/services/report/test_report_request_deps_factory.py -q`
- `cd backend && python -m py_compile app/services/report/report_factory_adapters.py app/services/report/report_runtime_factory.py app/services/report/report_runtime.py`

## 结论

这轮之后，report 侧工厂层边界更清楚了：

- adapters
- runtime factory
- workflow / canonical assembly

已经不再继续挤在一个层里。

## 下一步

- 继续盘点：
  - `report_runtime`
  - `report_request_workflow`
- 准备下一段 runtime 重整
