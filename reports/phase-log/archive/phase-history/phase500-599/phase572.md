# Phase 572 - analysis_collection_support 覆盖率汇总切到 runtime truth-source

## 发现了什么？
- `analysis_collection_support.fetch_coverage_summary()` 之前还在直接从 `community_cache` 汇总：
  - `backfill_status`
  - `coverage_months`
  - `sample_posts`
  - `sample_comments`
  - `backfill_capped`
- 但前一轮已经把 backfill 运行状态双写进了 `community_runtime_state`，所以这里继续读旧表会让报告摘要层口径滞后于 truth-source。

## 是否需要修复？
- 需要。
- 这是报告主链里的 coverage 摘要，不应该继续依赖旧 projection。

## 精确修复方法
### 1. 覆盖率汇总改读 runtime truth-source
- 更新：
  - `backend/app/services/analysis/analysis_collection_support.py`
- 改动：
  - `fetch_coverage_summary()` 现在改成联查：
    - `community_registry`
    - `community_runtime_state`
  - `backfill_status / coverage_months / backfill_capped` 从 `runtime_notes` 读取
  - `sample_posts / sample_comments` 从 `community_runtime_state` 读取

### 2. 新增定向回归
- 新增：
  - `backend/tests/services/analysis/test_analysis_collection_support.py`
- 覆盖：
  - coverage 汇总只读 runtime truth-source
  - missing community 仍然正确暴露

## 验证
- `pytest backend/tests/services/analysis/test_analysis_collection_support.py backend/tests/services/analysis/test_analysis_readiness_support.py backend/tests/services/analysis/test_analysis_finalization_support.py -q`
  - `9 passed`

## 下一步系统性的计划
- 继续扫剩余 API / report / worker 里的旧表正式判断点
- 现在重点只剩最后一些横向尾巴，要继续确认：
  - 是否还有直接拿 `community_pool` / `community_cache` 做正式判断的漏网点

## 这次执行的价值
- 这一步把报告摘要层的 coverage 口径也正式收进了 truth-source。
- 现在 backfill 状态不仅在 runtime 层被承接，连分析摘要和最终报告汇总也开始按同一套 runtime 真相源运行。
