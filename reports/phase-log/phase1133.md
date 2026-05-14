# Phase 1133: R16 品牌证据接入社区推荐解释

目的：让社区推荐不只靠活跃度和语义词，也能解释“这里有哪些真实品牌 / 平台讨论”。

当前状态变化：社区推荐 service 已读取 `brand-system-evidence` 的社区品牌证据，并合并到推荐解释；preview 重跑结果为 `tags=9 / recommendations=69 / ready_count=29 / acceptance_passed=true`，其中 `46` 条推荐带品牌证据。

关键边界：品牌证据只增强解释，不改排序、状态或 ready 判断；当前 `mention_count` 是品牌全局计数，不是社区内计数，不能拿来当算法权重。

还没完成：Hotpost 后续上下文的消费方式、高证据候选晋级队列和 API 高频读取索引还未做。

下一步：先审推荐质量，再决定是否进入 Hotpost 上下文接入和 API 读路径。
