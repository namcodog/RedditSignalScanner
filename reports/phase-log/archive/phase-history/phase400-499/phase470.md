# Phase 470 - Analysis Facts 后处理抽离

## 背景

在完成：

- `Evidence Selection`
- `Evidence Ledger`
- `Insight Synthesis`
- `Analysis Artifacts`

之后，`analysis_engine.py` 里还残留着一大段典型的纯后处理职责：

- 把评论样本整理成 comment signal input
- 把 comment signals 并回 facts
- 生成 `high_value_pains / brand_pain / solutions_block`
- 生成 `aggregates / source_range`

这些逻辑继续堆在 `analysis_engine.py` 里，会让主链同时承担：

- 采集编排
- 信号提取
- facts 后处理
- canonical 前置包装

边界还是不够干净。

## 本轮改动

### 1. 新增 facts support 模块

- 文件：`backend/app/services/analysis/analysis_facts_support.py`

新增：

- `CommentSignalPreparation`
- `FactsSignalArtifacts`
- `prepare_comment_signal_inputs(...)`
- `build_facts_signal_artifacts(...)`

### 2. 收窄 `analysis_engine.py`

- 文件：`backend/app/services/analysis/analysis_engine.py`

当前已从主链里搬走：

- comment lookup / comment signal input 组装
- business signals 与 comment signals 的 facts 合并
- `high_value_pains / brand_pain / solutions_block` 生成
- `aggregates / source_range` 生成

主链现在只保留：

- 评论样本加载
- comment extractor 调用
- facts package / data lineage 编排

### 3. 补齐定向测试

- 文件：`backend/tests/services/analysis/test_analysis_facts_support.py`

覆盖：

- comment signal input 过滤空评论
- 优先评论证据、再补帖子证据的既有合同
- solutions 缺失时回退到 opportunities 的既有合同

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py -q`
- `cd backend && python -m py_compile app/services/analysis/analysis_facts_support.py app/services/analysis/analysis_engine.py tests/services/analysis/test_analysis_facts_support.py`

## 结果

- `analysis_engine.py` 从 `5877` 行降到 `5741` 行
- 这轮没有改动对外 `Full A` 报告合同，只是把 comments/facts 这段纯后处理真正抽成了独立 support 层
- 主链又少了一块“越看越像 God Object”的职责

## 下一步

- 继续盘 `analysis_engine.py` 里剩余的大块
- 优先找：
  - 样本守卫 / 质量门禁
  - render 前置编排
  - 还能继续下沉到 support 模块的纯后处理
