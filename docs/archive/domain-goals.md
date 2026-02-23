# DEPRECATED

> 本文档已归档，不再作为当前口径。请以 docs/2025-10-10-文档阅读指南.md 指定的文档为准。

# 领域目标与覆盖要求（门禁/汇报基线）

目的：作为门禁与报告的对齐基线，明确每个领域的覆盖目标、最小命中、关键指标与说明。用于扩展 `content-acceptance` 断言，并指导抓取配额。

| domain | goal | min_communities | key_metrics | remarks |
|---|---|---:|---|---|
| 跨境选品 (what_to_sell) | 连续观察“新品类/爆品线索”与“众筹/平台新品” | 50 | 新品增速(7/30d)、讨论密度、证据≥2 | 结合 `kickstarter/indiegogo/Aliexpress/Etsy` 等渠道信号 |
| 营销/运营 (how_to_sell) | 归纳“高频打法/投放/转化”最佳实践 | 60 | 投放相关词频(PPC/ACoS/ROAS)、复盘帖密度、证据≥2 | 重点看 r/PPC、r/marketing、平台卖家社区 |
| 市场/渠道 (where_to_sell) | 识别“平台/区域渠道”机会优先级 | 60 | 渠道提及强度、区域热度(NA/EU/SEA)、证据≥2 | Amazon/Etsy/Shopify/TikTok Shop 等 |
| 供应链/合规/物流 (how_to_source) | 识别“采购/清关/仓配/关税”风险与机会 | 50 | 风险词频(延误/VAT/HS)、供应链事件密度、证据≥2 | r/Alibaba、r/freightforwarding、区域仓配论坛 |

门禁建议扩展（与 `content-acceptance` 集成）：
- 痛点簇 ≥ 2，且每簇跨社群证据 ≥ 2
- 竞品分层 ≥ 2 类（workspace/analytics/summary 至少两类出现）
- 机会项含 `potential_users_est > 0`，并与痛点簇有回链
- 域覆盖：各 domain 的 `min_communities` 达标（报告期内）

输出：
- 报告概览增加“领域覆盖进度条”（已覆盖/目标），并在摘要展示“缺口/建议”

