# Phase 262 - Round 3 收敛实现复核

## 目的
- 复核“historical_shells 收敛计划”在当前代码和当前 Dev 库里是否已真正落地
- 确认 Round 3 可以收尾，后续直接进入 Round 4

## 复核结论
- 当前治理服务已经具备以下行为：
  - `historical_shells` 单独输出
  - `summary.historical_shell_count` 单独统计
  - `cleanup_dev()` 不再把历史引用壳混进普通垃圾
  - cleanup 返回值包含 `targets.historical_shell_names`
- 当前 Dev 库治理快照已经收敛成：
  - `effective_pool_count = 141`
  - `candidate_count = 126`
  - `pool_garbage_count = 0`
  - `historical_shell_count = 48`
  - `discovered_garbage_count = 0`
  - `anomaly_count = 0`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_governance_service.py tests/api/test_admin_community_pool.py -q`
  - `13 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 当前统一口径
- `141` 个：真正生效社区
- `126` 个：候选社区
- `48` 个：历史引用壳
- 历史引用壳不是有效社区，也不是候选社区，只是历史 `posts_raw` 的外键挂点

## 结论
- Round 3 的最后收敛项已经在当前分支落地并通过验证
- 后续可以直接进入 Round 4 深度审计与执行计划
