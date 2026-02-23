# 阶段4 异常与机会（执行记录）

## 1) 去重/降频动作（高重复 t3 high 组）
- 目标：减少重复抓取浪费，对 dedup 高的 high 组社区降频。
- 已调整（14 个社区）：`crawl_frequency_hours=24`，`crawl_priority=90`
  - r/AmazonFBATips, r/Dropshipping_Guide, r/ecommercemarketing, r/ShopifyeCommerce, r/shopifyDev, r/FulfillmentByAmazon, r/dropshipping, r/MerchByAmazon, r/amazonecho, r/fuckamazon, r/Aliexpress, r/amazonprime, r/AmazonWTF, r/amazonfresh
- 说明：仅调整抓取频率/优先级，未改动正文数据。

## 2) 发现（后续处理方向）
- 空抓 t3（high/semantic，多为 empty_hit>0）：需要探针或降权。
- 热度爆发（30d vs 前30d）重点：amazonDSPDrivers、instacartshoppers、amazonfc、walmartemployees、amazonemployees、facebookads、amazonflexdrivers 等。
- 语义盲区：semantic_candidates 当前为空，需从高频未收录词生成候选。

## 3) 空抓社区降频
- 对 empty_hit>0 的 26 个社区，将 `crawl_frequency_hours=48`，`crawl_priority=95`（探针/降权，避免浪费）：AmazonWFShoppers, AntiAmazon, SuppliersInUSA, aliexpressreviews, WalmartAssociates, BestBuyAliexpress, AmazonFBAforNewbies, tiktok_shop_sellers, AmazonWarehouse, News_Walmart, ShopifyWebsites, FBAsourcing, marketing, AchadinhosDaShopeeBR, SEO, SEO_Marketing_Offers, EtsyHelp, Shopify_Users, EtsyUK, TikTokShopSellers, LazShop_PH, etsycirclejerk, lazadareviews, PrivateLabelSellers, AngelnmitAliexpress, ShopifyDevelopment。

## 4) 移除不相关社区（停用）
- 将与业务不相关的 11 个社区标记为停用（is_active=false，仅停用调度，未删除历史）：r/personalfinance, r/financialindependence, r/investing, r/artificial, r/ethereum, r/stocks, r/cryptocurrency, r/stockmarket, r/startups, r/bitcoin, r/cryptomarkets。

## 4) 高频未收录词（comments 近20k，去停用词/噪声）
- 当前简单抽取未收敛（常见词仍多）；需更严格过滤（去停用词+数字链接+已知品牌/通用词），再与 semantic_terms 比对，生成候选词清单（下一步执行）。

## 5) 下一步建议
- 对空抓社区：先探针，持续空则降权/移出。
- 对爆发社区：优先做痛点/品牌深挖（结合阶段3的热力/品牌榜）。
- 语义回流：提取高频未收录词（排除词库/黑名单），生成 candidates，人工审核后入 semantic_terms。

## 6) 热度爆发社区临时升优先（quality_tier=t1, crawl_priority=20）
- 社区（is_active=true）：AmazonDSPDrivers, InstacartShoppers, AmazonFC, WalmartEmployees, amazonemployees, FacebookAds, AmazonFlexDrivers, dropshipping, Aliexpress
- 说明：仅调整抓取优先级/质量分层，业务 tier 不变；可随热度回落再调回。
