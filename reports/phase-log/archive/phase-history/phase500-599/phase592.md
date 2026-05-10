# Phase 592 - pytest 社区表 destructive SQL 继续压缩

## 本轮目标
- 继续把需要社区表重置的测试收编到显式 fixture。
- 清掉更多“固定社区名 + 手写清表”的残留点。

## 主要动作
- `backend/tests/services/crawl/test_comments_ingest_service.py`
  - 把两处手写 `TRUNCATE comments/authors/posts_quarantine/posts_raw/community_pool` 改成显式 `async_truncate_test_tables`
  - 顺手把一条脆弱的日志捕获断言改成直接钩住模块 `logger.warning`
- `backend/tests/services/crawl/test_incremental_crawler_metrics.py`
  - 四处手写 `TRUNCATE community_cache/community_pool/...` 改成显式 `async_truncate_test_tables`

## 验证
- `cd backend && python -m pytest tests/services/crawl/test_comments_ingest_service.py tests/services/crawl/test_incremental_crawler_metrics.py -q`
  - `8 passed`

## 当前结果
- 手写 destructive community SQL 已从：
  - `13` 处 / `7` 个文件
- 继续下降到：
  - `7` 处 / `5` 个文件

## 剩余文件
- `backend/tests/services/community/test_dev_truth_source_compaction_service.py`
- `backend/tests/services/community/test_gold_dev_community_restore_service.py`
- `backend/tests/services/crawl/test_incremental_cold_storage_service.py`
- `backend/tests/services/crawl/test_incremental_crawler_dedup.py`
- `backend/tests/tasks/test_cleanup_soft_orphan_content_labels_entities.py`

## 结论
- 现在剩下的都是更偏“全链路重置型”或“恢复/压缩型”测试，已经不是大面积散落问题了。
- 这条 pytest 社区表安全重构已经进入最后清尾区。
