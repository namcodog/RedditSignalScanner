# Phase 473 - Analysis Readiness 支持抽离

## 背景

在上一轮把 `evidence_ledger / facts_slice / knowledge_graph` 这段输出装配抽到 `analysis_output_support.py` 之后，`analysis_engine.py` 里还残留一块很典型的主链杂糅职责：

- sample guard
- data readiness snapshot
- insufficient sample 早停结果装配

这三块都属于“样本与就绪状态支持层”，不该继续和主链编排绑在一起。

## 本轮改动

### 1. 新增 readiness support 模块

- 文件：`backend/app/services/analysis/analysis_readiness_support.py`

新增：

- `InsufficientSampleArtifacts`
- `run_sample_guard_check(...)`
- `build_data_readiness_snapshot(...)`
- `build_insufficient_sample_artifacts(...)`

### 2. 收窄 `analysis_engine.py`

- 文件：`backend/app/services/analysis/analysis_engine.py`

当前已从主链里搬走：

- sample guard 的执行与异常兜底
- data readiness snapshot 的构建
- insufficient sample 结果的 sources / report_html / confidence 装配

主链现在只负责：

- 传入任务上下文
- 调 readiness support 模块
- 再根据结果决定继续分析还是提前返回

### 3. 补齐定向测试

- 文件：`backend/tests/services/analysis/test_analysis_readiness_support.py`

覆盖：

- 空输入时 sample guard 返回 `None`
- sample guard 的 fetch / supplement 合同透传
- data readiness snapshot 的命中 / 缺失 / 聚合统计
- insufficient sample 早停合同

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_analysis_readiness_support.py tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py -q`
- `cd backend && python -m py_compile app/services/analysis/analysis_readiness_support.py app/services/analysis/analysis_engine.py tests/services/analysis/test_analysis_readiness_support.py`

## 结果

- `analysis_engine.py` 从 `5660` 行降到 `5497` 行
- analysis 主链又少了一块典型 support 职责
- 当前 analysis 侧分层继续变清楚：
  - evidence selection
  - evidence ledger
  - insight synthesis
  - analysis facts support
  - analysis output support
  - analysis readiness support
  - analysis artifacts

## 下一步

- 继续盘 `analysis_engine.py` 剩余大块
- 优先看：
  - render 前置编排
  - sources / confidence 周边
  - 还有没有样本守卫之外的质量门禁可继续下沉
