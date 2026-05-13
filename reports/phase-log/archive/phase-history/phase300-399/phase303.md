# Phase 303 - 第三轮第一刀：分析模块渲染 workflow 独立

## 背景

第三轮已经正式启动，目标从“可信闭环”继续推进到“本地产品级稳定”。

按 `系统总整治执行计划.md` 的第三轮顺序，第一刀仍然从分析模块下手。上一轮已经把：

- 检索计划
- 发现社区写库副作用

先从 `analysis_engine.py` 里拆出去了一层，但分析核心里仍然还挂着一整块“报告渲染 workflow”：

- 规则 markdown 渲染
- scouting 简报渲染
- 结构化 LLM 渲染
- blocked / scouting / A/B tier 的最终输出编排

这会让 `analysis_engine.py` 继续一边做分析，一边自己拼输出，不符合第三轮“继续降耦合、提内聚”的目标。

## 本轮动作

### 1. 新增独立渲染服务层

新增：

- `backend/app/services/analysis/analysis_rendering.py`

收口了这块原本挂在 `analysis_engine.py` 内部的职责：

- `StructuredReportRenderResult`
- `AnalysisReportRenderBundle`
- `format_collection_warning_lines(...)`
- `render_report(...)`
- `render_scouting_report(...)`
- `render_structured_report_with_llm(...)`
- `render_analysis_reports(...)`

大白话：

- 现在分析模块里的“报告怎么拼、怎么拦、怎么走结构化 LLM”开始有自己独立的齿轮了
- 不再继续让 `analysis_engine.py` 亲自下场拧这块输出逻辑

### 2. `analysis_engine.py` 收成更薄的编排层

`run_analysis(...)` 最后的渲染段改成：

- 先准备 `flags / suggestion`
- 再统一交给 `render_analysis_reports(...)`
- 最后只把 render bundle 回写到 `sources`

同时保留轻量兼容符号：

- `_render_report`
- `_render_scouting_report`
- `_render_report_with_llm`
- `_render_structured_report_with_llm`

这些名字现在只是从新模块导回，不再在 `analysis_engine.py` 内部保留整套实现。

### 3. 测试先行并锁住新边界

调整并新增：

- `backend/tests/services/analysis/test_analysis_engine.py`
- `backend/tests/services/analysis/test_analysis_rendering.py`

新增门禁点：

- `render_analysis_reports(...)` 在 `X_blocked` 场景下会返回统一 bundle
- 结构化 LLM 渲染测试不再绑死在 `analysis_engine` 内部实现，而是绑定新渲染模块

## 结果

### 结构结果

- `analysis_engine.py` 从“分析核心 + 输出 workflow 混编”继续收成更像“分析编排层”
- 报告渲染 workflow 现在有正式独立边界
- 第三轮第一刀真正落在“继续拆高耦合点”，不是只补状态字段

### 文件变化

- `backend/app/services/analysis/analysis_engine.py`
- `backend/app/services/analysis/analysis_rendering.py`
- `backend/tests/services/analysis/test_analysis_engine.py`
- `backend/tests/services/analysis/test_analysis_rendering.py`

### 体量变化

- `analysis_engine.py` 当前行数：`4981`
- 渲染 workflow 拆到新文件：`analysis_rendering.py`（`515` 行）

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/analysis/test_analysis_rendering.py \
  tests/services/analysis/test_analysis_engine.py -q
```

结果：

- `32 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 结论

这轮的价值不是“报告更好看了”，而是：

- 分析核心继续变薄
- 输出 workflow 继续独立
- `analysis_engine.py` 开始更像真正的分析中枢，而不是又算结论、又自己拼输出的大总管

一句大白话：

- 第三轮第一刀已经值回票价了，分析模块开始从“结构已经开始顺”继续往“更像产品级中枢”走。

## 下一步

按第三轮节奏，下一步继续打第二个最重的齿轮：

- `facts / 报告模块`

重点继续沿着同一条线：

- 继续拆 `ReportService`
- 继续压薄兼容壳
- 让 facts 整理、受控渲染、最终 payload 组装边界更单一
