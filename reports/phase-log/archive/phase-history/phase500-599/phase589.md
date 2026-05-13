# Phase 589 - pytest 社区表安全收尾第三轮

## 时间
- 2026-03-30

## 目标
- 继续压缩 truth-source 相关测试里的散装社区清表。

## 实施
- `backend/tests/services/community/test_truth_source_readiness_service.py`
  - `_cleanup_readiness_rows()` 改成使用 `async_truncate_test_tables`
  - 不再手写删除：
    - `community_runtime_state`
    - `community_governance_decision`
    - `community_domain_membership`
    - `community_registry`
  - `posts_raw / semantic_observation` 继续保留 scoped delete

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_truth_source_readiness_service.py -q`
  - `1 passed`

## 剩余尾巴
- 再次扫描后，剩余 destructive community SQL 已下降到：
  - `26` 处
  - `15` 个测试文件

## 当前结论
- pytest 社区表安全这条线已经不只是“默认不清”，而是在继续把 truth-source 相关测试的散装 destructive SQL 收编回统一 helper。
