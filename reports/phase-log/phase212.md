# Phase 212 - Comment Embeddings 接入与批次验证

## 目标
- 接入 comment_embeddings 表与任务
- 验证 posts/comments embeddings 批次可跑

## 执行
- 新增迁移：`20260302_000001_add_comment_embeddings.py`
- 任务接入：`backend/app/tasks/embedding_task.py`
  - 新增 comment embeddings 批次/全量任务
  - 修复 lookback_days 参数类型报错
- 路由接入：`backend/app/core/celery_app.py`
- Makefile 接入口：`backfill-comment-embeddings` / `backfill-comment-embeddings-batch`

## 结果（dev 库）
- posts embeddings：
  - 批次处理 200 条
  - 覆盖率：post_embeddings=186,926；missing=222,208
- comments embeddings：
  - comment_embeddings 表已创建
  - 批次处理 200 条
  - 当前规模：comment_embeddings=200；missing=2,180,315

## 补缺口进度
- 遇到问题：
  - batch=500 时 MPS 内存溢出（BGE-M3），已修复为内部 batch_size=64。
- 追加批次后（batch=500）：
  - post_embeddings=193,926；missing=215,480
  - comment_embeddings=3,200；missing=2,177,736
- 继续补缺口（batch=500 x10）：
  - post_embeddings=198,926；missing=210,529
  - comment_embeddings=8,200；missing=2,172,949
- 继续补缺口（posts batch=500 x50；comments batch=500 x50）：
  - post_embeddings=223,426；missing=186,238
  - comment_embeddings=33,200；missing=2,148,319
- 目标调整：
  - comments 有效池向量覆盖率目标：100%
  - 切换为 comments-only 12h 自动跑（logs/embeddings_comments_12h.log）
- 速度优化：高价值桶不足时用长尾补满到 500/批
- 完成情况：
  - comments 有效池向量覆盖率 100%（636,548 / 636,548）

## 备注
- 当前仅为批次验证，后续需持续批次/后台补齐缺口。
