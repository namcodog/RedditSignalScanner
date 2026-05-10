# Phase 596 - 语义库写入闭环接上主链，统一账本开始真实生效

## 本轮目标
- 把 `semantic_observation` 从“模型和测试里存在”推进到“主业务真的会刷新、主链真的会读”。
- 修掉语义库运行时最危险的两个漂移点：
  - 统一账本只在测试里同步
  - `UnifiedLexicon` 路径依赖当前工作目录

## 本轮落地
- 新增：
  - `backend/app/services/semantic/semantic_observation_runtime.py`
  - 统一封装：
    - `refresh_semantic_observations_for_contents(...)`
- 正式写入链已接上统一语义账本刷新：
  - `backend/app/services/llm/label_result_persistence.py`
  - `backend/app/services/llm/legacy_label_persistence.py`
  - `backend/app/services/labeling/labeling_posts.py`
  - `backend/app/services/labeling/comments_labeling.py`
- 统一词库路径口径已修正：
  - `backend/app/services/semantic/unified_lexicon.py`
  - 现在支持 repo-relative 路径解析，不再受当前 cwd 漂移影响
- 统一词库命中已开始给分类器提供更具体的 aspect：
  - `backend/app/services/semantic/text_classifier.py`
  - 例如 `pricingtrap` 这类命中不再只返回 `PAIN`，还能收成 `PRICE`
- 分析主链已开始真正消费统一语义账本：
  - `backend/app/services/analysis/analysis_signal_support.py`
  - 现在从 `semantic_observation` 归并：
    - `content_label`
    - `content_entity`
  - 不再直接依赖旧 `mv_analysis_labels / mv_analysis_entities`

## 这轮暴露并修掉的真实问题
- `semantic_observation_sync.py` 之前主业务没有实际接线，只在测试里跑。
- `comments_labeling.py` 里的评论查询方式不够稳，导致真实评论样本可能找不到。
- `UnifiedLexicon` 在 `backend/` 目录下运行时，`backend/config/...` 这种相对路径会漂，词库不一定按预期加载。
- `posts_raw` 在没有正式社区映射时会被隔离；这说明语义链路不是独立飘着的，它仍然受正式社区盘约束。
- `persist_comments(...)` 需要 Reddit 风格的 Unix `created_utc`，不能直接塞 Python `datetime`。

## 验证
- `cd backend && ../.venv/bin/python -m pytest tests/services/analysis/test_analysis_signal_support.py tests/services/semantic/test_integration_lexicon_classifier.py tests/services/labeling/test_comments_labeling_unified.py tests/services/labeling/test_labeling_pipeline.py tests/services/labeling/test_labeling_posts.py tests/services/semantic/test_semantic_observation_sync.py tests/services/semantic/test_unified_lexicon.py tests/services/llm/test_label_result_persistence.py tests/services/llm/test_legacy_label_persistence.py -q`
  - `22 passed`

## 当前结论
- 语义库这条线现在已经不是“半闭环”了：
  - 上游标签写入会刷新 `semantic_observation`
  - 下游至少已有一条真实分析读路径开始吃 `semantic_observation`
  - 统一词库路径也不再因为 cwd 漂移而失真
- 但它还没有像社区真相源那样 `100%` 收尾：
  - 仍有一批分析/报告模块继续直接读旧 `content_labels / content_entities`

## 下一步
1. 继续把分析/报告里剩余的旧语义读取口径切到 `semantic_observation`
2. 把语义层当前运行口径补进唯一数据库真相文档
3. 再回到报告主链，看剩余问题是否已经和语义库无关
