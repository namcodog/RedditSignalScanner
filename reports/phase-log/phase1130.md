# phase1130 - Brand Intelligence consumer-safe 合同收口

- 这轮达到的目的：把审计暴露的“默认输出不适合产品消费”修成后端合同，而不是只停在报告建议。
- 当前状态变化：新增 `brand_consumer_profiles.json` 和 consumer profile loader；API / CLI 默认走 `consumer_safe`，只返回 `verified` 品牌。
- 消费字段已收口：默认输出 `display_name / business_domains / interest_tags / evidence_status / display_status / mention_count`，内部治理字段只在 CLI `--profile internal_registry` 下输出。
- 验证结果：consumer-safe 预览仍为 `13` 个品牌、`710` 条证据，`db_writes=false / miniapp_snapshot_fields=false`。
- 还没完成：小程序 snapshot 未接，前端未接；索引和高证据候选晋级队列留到下一步。
- 下一步：把品牌注册表用于推荐解释、卡片证据和语义审核队列。
