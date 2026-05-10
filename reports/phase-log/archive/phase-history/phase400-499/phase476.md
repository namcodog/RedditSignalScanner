# Phase 476 - Analysis Evidence Package Support 抽离

## 时间
- 2026-03-25

## 背景
- 继续沿着分析主链重构推进，目标是不改 `Full A` 对外交付合同，只压缩 `analysis_engine.py` 的 God Object 体积和职责混杂。
- 这轮锁定的是 `run_analysis()` 里“证据打包”那一整段：
  - `sample_posts_db`
  - `sample_comments_db`
  - `comments_pipeline_status`
  - `comment_counts_by_subreddit`
  - 缺评论时的 remediation 调度

## 本轮动作

### 1. 新增证据打包 support 模块
- 新增：
  - `backend/app/services/analysis/analysis_evidence_package_support.py`
- 抽离能力：
  - `build_sample_posts_db(...)`
  - `derive_comments_pipeline_status(...)`
  - `fetch_comment_evidence(...)`
  - `CommentEvidenceArtifacts`

### 2. 主链改接新模块
- 更新：
  - `backend/app/services/analysis/analysis_engine.py`
- 变化：
  - 主链不再自己拼帖子样本和评论样本
  - 主链不再自己算评论流水线状态
  - 主链不再自己做评论缺失时的 remediation 调度包装

### 3. 补定向测试
- 新增：
  - `backend/tests/services/analysis/test_analysis_evidence_package_support.py`
- 覆盖：
  - sample posts 规范化
  - comments pipeline status 四种分支
  - comments evidence 的 sample/counts 构建
  - topic profile 下评论缺失时 remediation 触发

## 中途发现的问题
- 第一轮回归暴露出一个很具体的脏数据问题：
  - `comment_counts_by_subreddit` 出现 `r/r/paypal`
- 根因：
  - 评论 sample 在入表时已经做过一次社区名规范化
  - 后续统计 counts 时又重复做了一次 `normalise_community_name(...)`
- 修复：
  - 统计 counts 时直接使用已规范化的 `item["subreddit"]`
  - 不再二次规范化

## 验证
- 运行：
  - `cd backend && pytest tests/services/analysis/test_analysis_evidence_package_support.py tests/services/analysis/test_analysis_finalization_support.py tests/services/analysis/test_analysis_engine_search_grouping.py tests/services/analysis/test_analysis_engine_collection_mapping.py tests/services/analysis/test_analysis_readiness_support.py tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py tests/services/analysis/test_analysis_rendering.py -q`
  - `cd backend && python -m py_compile app/services/analysis/analysis_evidence_package_support.py app/services/analysis/analysis_finalization_support.py app/services/analysis/analysis_engine.py tests/services/analysis/test_analysis_evidence_package_support.py`
- 结果：
  - `28 passed`
  - `py_compile` 通过

## 结果
- `analysis_engine.py` 行数变化：
  - `4458 -> 4297`
- 当前累计减重曲线：
  - `5877 -> 5741 -> 5660 -> 5497 -> 4624 -> 4458 -> 4297`
- 这轮价值：
  - 证据打包不再散落在主链里
  - 评论证据链和帖子样本证据链开始有独立 support 合同
  - 为后续继续把 `analysis_engine.py` 压到 `3000` 打开了下一段空间

## 下一步
- 继续盘 `analysis_engine.py` 剩余大块
- 优先挑还能整块搬走的 support：
  - lineage / embedding / target-id support
  - 或 search / keyword / stopword support
- 继续用“大块减重 + 联合回归”的方式推进，不回头走补丁路线
