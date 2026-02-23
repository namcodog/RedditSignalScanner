# 阶段5 算法与配置校准（SOP落地稿）

## 统一反馈（五问）
- 发现了什么问题/根因：semantic_quality_score / tier 没有跟重算的 C 分和真实指标（pain 密度、avg_valid_posts、dedup_rate）对齐，高重复社区仍占用高频抓取；空抓社区缺少降权闭环，记录缺位。
- 是否已精确定位：已有可用信号（community_pool + community_cache + comments + content_labels），分位线缺口和 dedup/empty_hit 异常在 stage2/4 清单中已锁定。
- 精确修复方法：按 30 天窗口重算 C 分（痛点密度+评分替代 topic），算分位线后批量回写 semantic_quality_score/tier/quality_tier，并按 dedup/empty_hit 自动调频；每轮结果写 phase-log。
- 下一步做什么：跑“输入准备”SQL，生成 base 表 → 执行 C 分重算 & 分位线 → 按规则更新 tier/频率 → 输出榜单/异常/动作清单到本文件；若需要调去重策略，补充存储侧 dedup 开关或文本指纹。
- 这次修复的效果/结果：预期减少高重复抓取、提升热点社区抓取频次，tier 与真实质量一致，phase-log 可复盘每轮分位线和动作。

## 本轮校准步骤（对应 docs/sop/数据挖掘sop.md 阶段5）
1) 输入准备：用 SOP 中的 base SQL 拉 30 天窗口，补 freshness_hours、hit_30、dup_ratio、pain_density_90d、empty/成功比。
2) C 分重算：使用 pain_density+avg_score 作为 topic_score，activity=hit_30/50，freshness=1-72h 衰减，dup_rate 标准化到 0~1，得分封顶 100。
3) 分位线与分层：计算 C、pain_density、avg_valid_posts、dup_ratio 的 P50/P70/P90；按 high/medium/semantic 业务 tier 和 t1/t2/t3 抓取层更新 community_pool.tier、semantic_quality_score 以及 community_cache.quality_tier/crawl_frequency/priority。
4) 去重/抓频动作：dedup>50% → 48h/priority95 + 去重修复；dedup 30~50% → 12~24h；empty_hit>0 或 success_rate<0.6 → 探针一次，持续为空则降到 48h/95；高质量低重复 → 6h/priority≤30。
5) 结果输出：生成三张表并附规则版本号  
   - 榜单：community, C, pain_density, dup_ratio, avg_valid_posts, tier→tier_new, quality_tier→quality_tier_new, 建议动作。  
   - 异常：高重复、空抓、语义薄弱（pain_density<P40）、成功率低。  
   - 动作：提频/降频/去重/调级的 SQL 或脚本调用列表。

## 限制与已知问题
- 抓取/入库停在 2025-11-19（CST）；近 7 天没有新评论，近 30 天有历史存量可用。
- Serena MCP 自检超时（≈10s，握手失败），改用本地工具。

## 本轮跑数结果（2025-11-27，本地 DB，已用 *_key 规范化匹配）
- 社区覆盖：近30天评论 229,844 条，分布在 64 个社区；近7天=0（流水线停更）；近90天 395,394 条。
- 痛点标注：pain 标签 80,334 条，近30天与社区池匹配的痛点评论 8,046 条；pain_density 非零的社区 65 个。
- C 分（30天口径，topic=痛点密度+均分，activity=hit30/50，freshness=168h 衰减）：P50 57.67 / P70 61.88 / P90 65.46。近 7 天停更，freshness 成为主要扣分项。
- 高重复（>50%，16 个，已多为 24~48h/优先级高）：r/amazonfresh, r/MerchByAmazon, r/AmazonFlexDrivers, r/bigseo, r/Dropshipping_Guide, r/ecommercemarketing, r/AmazonFBATips, r/shopifyDev, r/ShopifyeCommerce, r/DropshippingTips, r/FulfillmentByAmazon, r/WalmartCanada, r/dropshipping, r/dropship, r/amazonecho, r/fuckamazon。
- 中重复（30~50%，6 个）：r/AmazonWTF, r/Aliexpress, r/InstacartShoppers, r/amazonreviews, r/shopify, r/amazonprime。
- 空抓（empty_hit>0，26 个，已降频 48h）：与 stage4 清单一致，如 r/AmazonWFShoppers, r/AntiAmazon, r/EtsyUK, r/TikTokShopSellers, r/LazShop_PH 等。
- T1 候选（按新 C 分 P70、低重复、无空抓）：r/Legomarket, r/AmazonSeller, r/AmazonWFShoppers, r/SpellcasterReviews, r/EtsySellers；但 freshness 受 7 天停更影响，提频需等抓取恢复。
- 成功率 <60% 的 27 个，与空抓高度重合，等恢复抓取后再评估。
- 根本修复：新增 computed 列 community_pool.name_key / community_cache.community_key（去 r/ 前缀+小写），已跑迁移 20251127_000040，JOIN 统一用 *_key 对齐 comments.subreddit，防止再出现“全 0”。

## 建议动作（未执行，待数据补齐后统一应用）
1) 数据修复优先：确认 comments 与 pain 标注入库是否缺失；可先拉 90 天评论全量和标签再跑重算，否则 C 分和分层无意义。
2) 去重/降频：保持高重复组在 48h/priority 95，复查 dedup 算法；中重复组降到 12~24h，并在去重修复后再提频。
3) 空抓探针：对空抓组保留 48h 探针；如补数据后仍空，考虑停用或进一步降权。
4) 记录口径：本轮未做任何 DB 更新，只做读和导出；待数据补齐后按 SOP 再跑一次并回填 tier/quality_tier/频率。
