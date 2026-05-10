# Phase 593 - pytest 社区表安全线正式收尾

## 本轮目标
- 清掉最后残留的手写 `community_*` destructive SQL。
- 确认 pytest 社区表安全线已经真正归零。

## 主要动作
- `backend/tests/services/community/test_dev_truth_source_compaction_service.py`
  - 手写 `TRUNCATE community_* ...` 改成显式 `async_truncate_test_tables`
- `backend/tests/services/community/test_gold_dev_community_restore_service.py`
  - 去掉 `_cleanup()` 中对 `community_category_map/community_cache/community_pool` 的手写删除
  - 改成唯一社区名隔离
- `backend/tests/services/crawl/test_incremental_cold_storage_service.py`
  - class 级 autouse reset 改成显式 `async_truncate_test_tables`
- `backend/tests/services/crawl/test_incremental_crawler_dedup.py`
  - class 级 autouse reset 改成显式 `async_truncate_test_tables`
- `backend/tests/tasks/test_cleanup_soft_orphan_content_labels_entities.py`
  - 手写 `TRUNCATE ... community_pool` 改成显式 `async_truncate_test_tables`

## 验证
- `cd backend && python -m pytest tests/services/community/test_dev_truth_source_compaction_service.py tests/services/community/test_gold_dev_community_restore_service.py -q`
  - `4 passed`
- `cd backend && python -m pytest tests/services/crawl/test_incremental_cold_storage_service.py tests/services/crawl/test_incremental_crawler_dedup.py tests/tasks/test_cleanup_soft_orphan_content_labels_entities.py -q`
  - `16 passed`
- destructive SQL 复扫：
  - `community_*` 手写 `DELETE/TRUNCATE` -> `0`

## 结果
- “默认 pytest 不清社区表” 这条重构现在不只是主路径安全，而是测试仓库里残留的手写社区表 destructive SQL 也已经清零。
- 现在如果测试要重置社区表，必须通过显式 fixture。

## 结论
- pytest 社区表安全线已经正式收尾。
- 后续如果再出现手写 `community_*` destructive SQL，应该视为回归问题，而不是正常测试写法。
