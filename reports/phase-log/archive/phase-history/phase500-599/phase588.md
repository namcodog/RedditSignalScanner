# Phase 588 - pytest 社区表安全收尾第二轮

## 时间
- 2026-03-30

## 目标
- 修掉 pytest 社区表迁移第一批里的公共阻塞。
- 继续把高影响 `community_*` destructive tests 收编进统一路径。

## 发现
1. `test_planner_workflow.py` 全文件失败的根因不是业务逻辑，而是测试生命周期：
   - 每个 async 测试函数都会创建新 event loop。
   - 但全局 SQLAlchemy async engine 连接池没有在 loop 关闭前销毁。
   - 下一个测试会拿到绑定旧 loop 的连接，触发 `Future attached to a different loop`。
2. 默认 pytest 不再清社区表之后，一批旧测试暴露出隐含假设：
   - 它们默认测试库一开始就是空的。
   - 所以不能只把手写 `TRUNCATE` 换个地方放，还要补明确的局部边界。

## 实施
1. 公共修复
   - `backend/tests/conftest.py`
   - 在 `event_loop` fixture teardown 中增加 `engine.dispose()`。
   - 让每个 async 测试在关闭 loop 前先销毁全局 async engine 连接池。

2. 第二批高影响测试迁移
   - `backend/tests/services/community/test_community_governance_service.py`
     - 4 处手写 `TRUNCATE community_*` 改为 `async_truncate_test_tables`
   - `backend/tests/api/test_admin_community_pool.py`
     - 治理摘要测试改为 `async_truncate_test_tables`
     - 同时改成局部 `SessionFactory()`，不再把显式 truncate 和长期 `db_session` 混在一起
   - `backend/tests/services/community/test_candidate_vetting_service.py`
     - 删除固定社区名 + 手写删除
     - 改成每次生成唯一社区名，彻底去掉前置 `DELETE community_pool`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/crawl/test_planner_workflow.py -q`
  - `3 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_governance_service.py -q`
  - `7 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/api/test_admin_community_pool.py -q -k governance_summary_effective_and_cleanup`
  - `1 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_candidate_vetting_service.py -q`
  - `4 passed`
- 组合回归：
  - `10 passed`

## 当前结果
- pytest 默认路径不清社区表这件事已经站住了。
- `planner_workflow` 的跨事件循环失败已从公共生命周期层面根治。
- 第一批高影响 destructive community tests 已经收编完成。

## 剩余尾巴
- 还剩 `30` 处 `community_*` destructive SQL。
- 分布在 `16` 个测试文件里，下一批优先级：
  1. `backend/tests/services/community/test_truth_source_readiness_service.py`
  2. `backend/tests/services/community/test_evaluator_service.py`
  3. `backend/tests/services/crawl/test_incremental_crawler_metrics.py`

## 结论
- 这轮不是补丁，而是把“默认不清社区表”背后的测试生命周期问题一起收掉了。
- 后面继续推进时，优先消灭剩余散装 destructive SQL，不再回到“测试默认就动社区表”的旧架构。
