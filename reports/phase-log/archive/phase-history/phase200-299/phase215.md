# Phase 215

## 目标
- 为每条帖子抓取 Top 3 评论并限制长度。

## 变更
- 评论抓取截断与限量：`backend/app/services/hotpost/service.py`
  - `fetch_post_comments` 结果限制为 Top 3
  - 评论正文截断至 400 字符
- 评论抓取覆盖 Top 30 帖：`backend/app/services/hotpost/service.py`

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_comments.py -q`

## 结论
- Phase 215 完成，评论抓取与长度控制已落地。
