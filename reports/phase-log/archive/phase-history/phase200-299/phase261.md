# Phase 261 - 社区治理再次收敛（historical_shells 正式分流）

## 执行时间
- 2026-03-14

## 背景
- Phase 259 已完成 Dev 库真实整治：
  - `community_pool` 垃圾硬删 142
  - `community_cache` 删除 190
  - `discovered_communities` 垃圾删除 39
- Phase 260 已核实：
  - 当前 141 个生效社区 100% 覆盖 8 大领域
  - 剩余 48 个不是有效社区，而是挂着 `posts_raw` 的历史引用壳
- 本轮目标：
  - 把这 48 个从“普通垃圾”里正式拆出去
  - 让治理快照和 summary 一眼就能看懂

## 本轮变更

### 1. 治理快照新增 `historical_shells`
- `CommunityGovernanceService.build_snapshot()` 现在把非有效 pool 行拆成两类：
  - `garbage_communities.pool`
    - 可清理的普通垃圾
  - `historical_shells`
    - 被历史引用卡住、不能直接物理删除的旧壳

### 2. summary 新增 `historical_shell_count`
- 现在治理 summary 里能直接看到：
  - `pool_garbage_count`
  - `historical_shell_count`
- 不再把 48 个旧壳混在 `pool_garbage_count` 里

### 3. cleanup 返回值同步收口
- `cleanup_dev()` 现在会返回：
  - `targets.historical_shell_names`
  - `blocked_items.pool`
- 这批不会被误当成“还没清的普通垃圾”

### 4. 测试收口
- 治理服务测试补了：
  - 历史引用壳在快照里单列
  - cleanup 只删普通垃圾，不删历史壳
- API 测试补了：
  - `summary.historical_shell_count`

## 当前 Dev 库真实快照（再次收敛后）
- 数据库：`reddit_signal_scanner_dev`

| 指标 | 数量 |
| --- | ---: |
| 生效社区 | 141 |
| 候选社区 | 126 |
| 普通 pool 垃圾 | 0 |
| 历史引用壳 | 48 |
| discovered 垃圾 | 0 |
| 异常 | 0 |

## 当前统一口径

### 真正生效的社区
- `community_pool`
- 且满足：
  - `is_active = true`
  - `deleted_at is null`
  - `is_blacklisted = false`
- 当前数量：`141`

### 候选社区
- `discovered_communities`
- 当前数量：`126`

### 历史引用壳
- 当前数量：`48`
- 这些不是有效社区
- 这些不是候选社区
- 这些只是历史 `posts_raw` 的外键挂点

## 本轮价值
- 社区治理视图终于不再把“还能删的垃圾”和“不能删的历史壳”混在一起
- 人看 summary，不会再误会“还有 48 个垃圾没处理”
- AI 看快照，也不会再把这 48 个旧壳误当成当前活跃池的一部分

## 输出文件
- 本轮快照：
  - `reports/phase-log/phase261_governance_snapshot.json`
- 本轮记录：
  - `reports/phase-log/phase261.md`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_governance_service.py tests/api/test_admin_community_pool.py -q`
  - `13 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 结论
- 现在 DB 里和社区治理有关的三类东西，终于能明确分开看：
  - `141` 个生效社区
  - `126` 个候选社区
  - `48` 个历史引用壳
- 这一步不是继续删数据，而是把“数据语义”说清楚
