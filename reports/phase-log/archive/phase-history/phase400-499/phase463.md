# Phase 463 - Insight Synthesis 第一段抽离

## 背景

在完成：

- `Worker / State Orchestration`
- `Evidence Selection`
- `Evidence Ledger`
- `Report 侧 Evidence Ledger 接线`

之后，下一步必须继续拆的是 `Insight Synthesis`。

如果 pain / opportunity 的组装还继续堆在 `analysis_engine.py` 里，那么：

- evidence 已经统一了
- report 也开始统一读账本了

但“洞察怎么从证据长出来”这一步仍然会继续被 God Object 吞掉。

## 本轮改动

### 1. 新增 Insight Synthesis 模块

- 文件：`backend/app/services/analysis/insight_synthesis.py`

当前先抽了第一段：

- `build_pain_points_payload(...)`
- `build_opportunities_payload(...)`
- `pick_linked_pain_cluster(...)`
- `clean_opportunity_copy(...)`

### 2. 将 pain / opportunity 组装从 analysis 主链抽出

- 文件：`backend/app/services/analysis/analysis_engine.py`

此前这两段都直接内联在 `run_analysis()` 大函数里。

现在改成：

- `analysis_engine.py` 负责编排
- `insight_synthesis.py` 负责组装

这意味着主链开始真正往“边界清楚的流水线”收。

### 3. 补齐定向测试

- 文件：`backend/tests/services/analysis/test_insight_synthesis.py`

当前验证了两件事：

- pain 会优先回落到中文业务表达，并过滤掉英文脏例句
- opportunity 会正确挂到 pain cluster，并保留更适合账本/报告消费的文案结构

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_insight_synthesis.py -q`
- `cd backend && python -m py_compile app/services/analysis/insight_synthesis.py app/services/analysis/analysis_engine.py`

## 结论

这轮之后，`Insight Synthesis` 已经从概念进入代码层：

- pain 组装开始独立
- opportunity 组装开始独立

这还不是整个 synthesis 完成态，但已经把两段最容易继续堆领域逻辑的路径先抽了出来。

## 下一步

- 继续往下拆：
  - driver
  - battlefield
  - action report
- 目标是继续压缩 `analysis_engine.py`，让它回到真正的主流程编排层。
