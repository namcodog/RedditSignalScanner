# Phase 464 - Insight Synthesis 第二段抽离

## 背景

在完成 pain / opportunity 第一段抽离之后，`analysis_engine.py` 里还有一组明显不该继续留在主链里的洞察后处理：

- `action_items`
- `entity_summary`
- `channel_breakdown`
- `battlefield_profiles`
- `top_drivers`

如果这组逻辑不继续往外拆，`analysis_engine.py` 仍然会停留在“主链编排 + 洞察后处理 + 报告预装配”混在一起的状态。

## 本轮改动

### 1. 扩展 Insight Synthesis 模块

- 文件：`backend/app/services/analysis/insight_synthesis.py`

新增：

- `InsightSynthesisSummary`
- `finalize_insights_summary(...)`

当前这个入口开始统一承接：

- action item 生成
- entity summary / channel breakdown
- battlefield profiles
- top drivers

### 2. 压缩 analysis 主链

- 文件：`backend/app/services/analysis/analysis_engine.py`

此前这几段都直接内联在主链里。

现在改成：

- `analysis_engine.py` 负责把上下文准备好
- `insight_synthesis.py` 负责做洞察后处理

这意味着主链继续往“只做编排”的目标靠近。

### 3. 扩展定向测试

- 文件：`backend/tests/services/analysis/test_insight_synthesis.py`

新增验证：

- action item 会被正确挂到机会描述
- battlefield 会读社区和痛点计数
- top drivers 会读 pain 和 action item

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_insight_synthesis.py -q`
- `cd backend && python -m py_compile app/services/analysis/insight_synthesis.py app/services/analysis/analysis_engine.py`

## 结论

这轮之后，`Insight Synthesis` 已经从第一段的 pain / opportunity 组装，继续扩展到了主要洞察后处理。

也就是说：

- `analysis_engine.py` 不再直接持有这组组装细节
- `insight_synthesis.py` 开始成为真正的洞察组装层

## 下一步

- 继续盘点是否还有剩余 synthesis 责任留在主链
- 然后开始切入 `Canonical Report Assembly`
