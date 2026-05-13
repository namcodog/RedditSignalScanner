# Phase 472 - Analysis 输出装配抽离

## 背景

在上一轮把 comments/facts 纯后处理抽到 `analysis_facts_support.py` 之后，`analysis_engine.py` 里还残留一块典型“输出装配杂活”：

- `evidence_ledger`
- `facts_slice`
- `knowledge_graph`

这三块都属于“把分析结果整理成报告消费面”的输出装配，不该继续堆在主链里。

## 本轮改动

### 1. 新增 output support 模块

- 文件：`backend/app/services/analysis/analysis_output_support.py`

新增：

- `AnalysisOutputArtifacts`
- `build_knowledge_graph(...)`
- `build_analysis_output_artifacts(...)`

### 2. 收窄 `analysis_engine.py`

- 文件：`backend/app/services/analysis/analysis_engine.py`

当前已从主链里搬走：

- `evidence_ledger` 构建与挂载
- `facts_slice` 构建
- `knowledge_graph` 构建

主链现在只负责：

- 准备输入
- 调 output support 模块
- 继续往 `sources / render / confidence` 走

### 3. 补齐定向测试

- 文件：`backend/tests/services/analysis/test_analysis_output_support.py`

覆盖：

- knowledge graph 的 evidence / driver / community 装配
- `facts_v2_package -> evidence_ledger -> facts_slice -> knowledge_graph` 串联合同
- 缺 package 时返回空 artifacts 的合同

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py -q`
- `cd backend && python -m py_compile app/services/analysis/analysis_output_support.py app/services/analysis/analysis_engine.py tests/services/analysis/test_analysis_output_support.py`

## 结果

- `analysis_engine.py` 从 `5741` 行降到 `5660` 行
- analysis 主链又少了一块纯输出装配职责
- 当前 analysis 侧分层继续变清楚：
  - evidence selection
  - evidence ledger
  - insight synthesis
  - analysis facts support
  - analysis output support
  - analysis artifacts

## 下一步

- 继续盘 `analysis_engine.py` 剩余大块
- 优先看：
  - sample guard / data readiness
  - render 前置编排
  - confidence / sources 周边还能不能继续收窄
