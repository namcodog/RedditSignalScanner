# Phase 478 - Analysis Signal Support 抽离

## 时间
- 2026-03-25

## 背景
- 继续按“只拆内部边界，不改 `Full A` 对外交付合同”的口径推进分析主链重构。
- 这轮锁定的是 `analysis_engine.py` 中另一整块介于工具层和分析层之间的 support：
  - data lineage
  - target id 截断与 ID 识别
  - post embeddings 读取
  - label-based business signals 聚合
  - hybrid posts merge

## 本轮动作

### 1. 新增 signal support 模块
- 新增：
  - `backend/app/services/analysis/analysis_signal_support.py`
- 抽离能力：
  - `normalize_target_ids(...)`
  - `looks_like_reddit_post_id(...)`
  - `truncate_target_ids(...)`
  - `build_data_lineage(...)`
  - `merge_posts_by_id(...)`
  - `parse_embedding_value(...)`
  - `fetch_post_embeddings(...)`
  - `extract_business_signals_from_labels(...)`

### 2. 主链改接新模块
- 更新：
  - `backend/app/services/analysis/analysis_engine.py`
- 变化：
  - 主链不再自己背 data lineage 拼装
  - 主链不再自己背 embedding 解析和 DB 读取
  - 主链不再自己背 label-based signals 聚合
  - 顺手清掉已经没有引用的 `_tokenise(...)`

### 3. 补定向测试
- 新增：
  - `backend/tests/services/analysis/test_analysis_signal_support.py`
- 覆盖：
  - target ids 截断与 data lineage 合同
  - embedding 解析与 Reddit post id 识别
  - post embeddings 读取
  - label-based signals 聚合

## 中途发现的问题
- 第一轮回归暴露出一个很具体的合同遗漏：
  - `BusinessSignals` 构造时还需要 `solutions`
- 根因：
  - 新 support 在迁移时只带了 `pain_points / competitors / opportunities / ps_ratio`
  - 漏掉了当前数据合同中的 `solutions`
- 修复：
  - 返回 `BusinessSignals(...)` 时补上 `solutions=[]`
  - 收回到当前真实合同

## 验证
- 运行：
  - `cd backend && pytest tests/services/analysis/test_analysis_signal_support.py tests/services/analysis/test_analysis_query_support.py tests/services/analysis/test_analysis_evidence_package_support.py tests/services/analysis/test_analysis_finalization_support.py tests/services/analysis/test_analysis_engine_search_grouping.py tests/services/analysis/test_analysis_engine_collection_mapping.py tests/services/analysis/test_analysis_readiness_support.py tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py tests/services/analysis/test_analysis_rendering.py -q`
  - `cd backend && python -m py_compile app/services/analysis/analysis_signal_support.py app/services/analysis/analysis_query_support.py app/services/analysis/analysis_engine.py tests/services/analysis/test_analysis_signal_support.py`
  - `cd backend && wc -l app/services/analysis/analysis_engine.py`
- 结果：
  - `36 passed`
  - `analysis_engine.py = 3387` 行

## 结果
- `analysis_engine.py` 行数变化：
  - `3718 -> 3387`
- 当前累计减重曲线：
  - `5877 -> 5741 -> 5660 -> 5497 -> 4624 -> 4458 -> 4297 -> 3718 -> 3387`
- 这轮价值：
  - 主链又少了一大段“既像工具层又像分析层”的 support
  - `analysis_engine.py` 已经离 `3000` 只差 `387` 行
  - 这说明冲到 `3000` 不是概念目标，而是已经进入最后冲刺

## 下一步
- 继续盘 `analysis_engine.py` 最后 `387` 行还能整块搬走的部分
- 优先看：
  - `run_analysis()` 中部剩余的 side-effect 协调
  - backfill / remediation 预算 support
  - post score / dedup / noise policy 周边 support
