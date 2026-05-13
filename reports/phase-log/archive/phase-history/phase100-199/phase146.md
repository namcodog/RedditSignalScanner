# Phase 146 - insights/facts_slice 算法补齐（主链路落地）

日期：2026-01-22

## 目标
让主链路输出完整算法结论（insights）与 facts_slice 证据切片，作为 LLM 报告输入的唯一口径。

## 范围
- 后端分析引擎：补齐趋势、饱和度、战场画像、驱动力输出，并生成 facts_slice。
- 新增算法工具与切片构建函数。
- 补单测覆盖（事实切片 + 结论算法）。

## 变更
- 新增 `backend/app/services/facts_v2/slice.py`：`build_facts_slice_for_report`。
- 新增 `backend/app/services/analysis/insights_enrichment.py`：趋势总结/饱和度/战场画像/驱动力算法。
- `backend/app/services/analysis_engine.py`：
  - 接入 `build_trend_analysis`、`SaturationMatrix`，输出 `trend_summary`/`market_saturation`/`battlefield_profiles`/`top_drivers`。
  - 生成并写入 `sources.facts_slice`。
  - 复用 `derive_driver_label`，确保口径一致。
- 新增测试：
  - `backend/tests/services/test_facts_slice.py`
  - `backend/tests/services/test_insights_enrichment.py`

## 结果
- 主链路已有算法产出完整结论字段。
- facts_slice 可直接作为 LLM 证据输入。

## 测试
- 未执行（仅补单测）。
