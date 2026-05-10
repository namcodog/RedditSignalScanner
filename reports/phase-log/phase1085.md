# phase1085

- 这轮达到的目的：把 Reddit Community Intelligence Phase 0 纠偏为社区治理审计，不改 DB / API / 前端 / 小程序。
- 当前状态变化：新增社区治理规则文档和只读 `community_governance_audit.py`，读取 Hotpost published cards、`community_pool`、`discovered_communities` 和 supply config。
- 验收结果：审计输出 `promote_candidate=69 / keep_active=39 / needs_evidence=31 / stale_review=115 / observation_queue=10`，报告已生成到 `reports/community-governance/phase0-audit.md`。
- 还没完成什么：这不是推荐算法通过，也不是产品入口；`CommunityDiscoveryService` dry-run、`community_ranker`、语义相关性和持久化快照全部延后到 Phase 1。
- 下一步做什么：人工审 `phase0-audit.md` 的推进 / 保留 / 缺证据 / 旧资产复核 / 归类错误列表，再开 Phase 1 治理与语义审查。
