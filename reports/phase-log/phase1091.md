# phase1091 - Community Intelligence 口径纠偏

这轮目的：把主项目新方向从 Phase 0 / 1 / 2 的社区治理合同里拆出来，避免继续把数据准备误当成产品完成。

当前状态变化：新增 `docs/reference/community-intelligence-clean-contract-2026-05-07.md`，明确当前主线是“系统标签 / 赛道 -> 有证据、有理由、长尾优先的社区推荐”。`community_pool` 是社区总池，不是推荐面；Hotpost 是新社区探测器，不能用没出卡否定旧 DB 社区。

还没完成：标签式推荐预览、`15D` 活跃探测、旧 DB + Hotpost + 发现链证据融合还没有落成产品闭环。

下一步：先做离线推荐预览，不上前端、不写 Gold、不重启开放检索框；复用 `CommunityDiscoveryService` 和 `community_ranker` 前先审计适配点。
