# Phase 475 - Analysis Finalization Support 抽离

## 背景

在把 collection / routing support 整块搬出之后，`analysis_engine.py` 尾部还留着一段典型“主链尾巴过长”问题：

- facts_v2 质量门禁
- report tier 降级
- trend summary 补入
- sources payload 组装
- render bundle 调用
- confidence score 计算

这段逻辑本质上属于“最终交付前的收口层”，不该继续滞留在 orchestrator 里。

## 本轮改动

### 1. 新增 finalization support 模块

- 文件：`backend/app/services/analysis/analysis_finalization_support.py`

新增：

- `QualityGateArtifacts`
- `FinalizedAnalysisOutputs`
- `calculate_confidence_score(...)`
- `apply_quality_gate_to_insights(...)`
- `apply_trend_summary_if_needed(...)`
- `finalize_analysis_outputs(...)`

### 2. 收窄 `analysis_engine.py`

- 文件：`backend/app/services/analysis/analysis_engine.py`

当前已从主链里搬走：

- quality gate / tier 结果整理
- trend summary 追加
- sources payload 最终装配
- render bundle 调用后的 structured / llm 字段回填
- confidence score 计算

主链现在更接近：

- 准备分析输入
- 调用各 support / synthesis / artifacts
- 调 finalization support
- 返回 `AnalysisResult`

### 3. 补齐定向测试

- 文件：`backend/tests/services/analysis/test_analysis_finalization_support.py`

覆盖：

- confidence score 的范围与封顶
- insufficient sample 的保守降级合同
- trend summary 的 coverage 降级注入
- finalization 对 sources / render / llm 元数据 / confidence 的串联合同

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_analysis_finalization_support.py tests/services/analysis/test_analysis_engine_search_grouping.py tests/services/analysis/test_analysis_engine_collection_mapping.py tests/services/analysis/test_analysis_readiness_support.py tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py tests/services/analysis/test_analysis_rendering.py -q`
- `cd backend && python -m py_compile app/services/analysis/analysis_finalization_support.py app/services/analysis/analysis_engine.py tests/services/analysis/test_analysis_finalization_support.py`

## 结果

- `analysis_engine.py` 从 `4624` 行降到 `4458` 行
- analysis 主链尾部又少了一整段最终收口逻辑
- 相关回归 `24 passed`
- 对外 `Full A` 报告合同没有变化

## 下一步

- 继续盘 `analysis_engine.py` 剩余大块
- 优先看：
  - render 前置编排
  - 还有没有残留在主链里的数据整形 / side-effect 协调
  - 能否再整块搬走一段 `run_analysis()` 中部逻辑
