# Phase 465 - Analysis Artifacts / Canonical 前置抽离

## 背景

在连续完成：

- `Evidence Selection`
- `Evidence Ledger`
- `Insight Synthesis`

之后，`analysis_engine.py` 里还有一大段纯后处理包装逻辑仍然挤在主链里：

- `facts_v2_package`
- `report_tier` 降级
- `sources` 组装

这些逻辑虽然重要，但并不应该继续和主链流程强耦合。

## 本轮改动

### 1. 新增 artifacts 模块

- 文件：`backend/app/services/analysis/analysis_artifacts.py`

当前抽离出的函数：

- `build_facts_v2_package(...)`
- `attach_aggregates(...)`
- `apply_report_tier(...)`
- `build_sources_payload(...)`

### 2. 主链改接 artifacts

- 文件：`backend/app/services/analysis/analysis_engine.py`

此前这几段都在 `run_analysis()` 里直接展开。

现在改成由 artifacts 模块统一承接。

### 3. 补齐定向测试

- 文件：`backend/tests/services/analysis/test_analysis_artifacts.py`

覆盖了：

- facts package 组装
- report tier 降级
- sources 组装合同

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_analysis_artifacts.py -q`
- `cd backend && python -m py_compile app/services/analysis/analysis_artifacts.py app/services/analysis/analysis_engine.py`

## 结果

这轮之后，`analysis_engine.py` 又少了一块纯包装后处理。

但也因此更清楚地看到一个事实：

- 当前 `analysis_engine.py` 仍然有 `5877` 行

这说明继续拆分不是“洁癖式优化”，而是必要的结构治理。

## 下一步

- 继续盘点主链剩余职责
- 正式切入 `Canonical Report Assembly`
