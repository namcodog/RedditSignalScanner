# Phase 203 - KAG P0 向量写入自动化

## 执行范围
- Celery beat 增加 embeddings 周期任务
- SOP/PRD/Makefile 口径同步

## 变更明细
- 新增 beat 任务：
  - embeddings-backfill-posts（maintenance_queue，默认每小时）
  - embeddings-backfill-comments（maintenance_queue，默认每小时）
- 新增环境开关：
  - EMBEDDING_BEAT_ENABLED=0（关闭全部向量自动补齐）
  - EMBEDDING_COMMENTS_BEAT_ENABLED=0（仅关闭 comments）

## 文档同步
- docs/sop/数据清洗打分规则v1.2规范.md：新增向量写入自动化口径
- docs/prd/PRD-03-分析引擎.md：补充向量写入自动化说明
- Makefile：data-embeddings 说明更新

## 验收口径
- beat 任务启用后，post_embeddings/comment_embeddings 应持续增长
- analysis_engine 中 hybrid_posts_used / dedup_stats 可正常产出

## 差异说明
- 无
