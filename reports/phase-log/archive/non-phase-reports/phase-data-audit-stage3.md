# 阶段3 价值密度与痛点热力（执行记录）

## 1) T1 社区 × 痛点类型（Top 若干）
- 主要痛点集中：amazonflexdrivers（other/subscription/price/install）、etsy（subscription/other/price/content）、legomarket（subscription）、facebookads（subscription/other/price/content）、etsysellers、dropship、amazonseller、bigseo、walmartcanada、spellcasterreviews 等。
- 用法：可直接做热力图/榜单（社区×pain aspect）。

## 2) 品牌榜（临时方案：评论正文正则匹配，黑名单去噪，频次≥20）
- amazon 97,664 / 平均分 4.4 / 痛点占比 13.9%
- walmart 18,618 / 8.0 / 10.5%
- etsy 16,832 / 7.2 / 20.9%
- google 14,983 / 3.1 / 11.9%
- shopify 14,915 / 1.9 / 7.4%
- target 10,252 / 3.2 / 21.1%
- aliexpress 9,591 / 5.4 / 10.6%
- meta 8,140 / 2.6 / 11.6%
- tiktok 7,190 / 2.1 / 20.4%
- ebay 6,833 / 4.9 / 9.8%
- youtube 6,274 / 3.2 / 24.3%
- facebook 5,699 / 3.5 / 11.9%
- usps 3,324 / 4.6 / 14.6%
- instagram 3,315 / 2.7 / 32.2%
- paypal 2,926 / 2.8 / 34.1%
- software 2,594 / 3.3 / 14.4%
- chatgpt 2,232 / 2.9 / 9.0%
- sku 1,834 / 2.6 / 17.8%
- conversion rate 1,275 / 2.6 / 11.9%
- ugc 1,081 / 2.0 / 11.7%
说明：因 `content_entities` 映射缺陷，暂用评论正文匹配品牌词（黑名单去噪、统一小写）。这是临时榜单，正式品牌榜待实体映射修复后重算。

## 3) 品牌实体链路问题与修复要求
- 发现：`content_entities` 的 post 类型 content_id 无法对上 `posts_raw.id`（关联为0）；comment 类型品牌实体仅 ~761 条，覆盖很低，导致品牌×痛点/评分无法可靠计算。
- 修复清单（必须完成后再算正式品牌榜）：
  1) 确认并纠正 content_entities.content_id 映射到 posts_raw.id / comments.id，必要时迁移已有数据。
  2) 补充评论侧实体抽取，提升覆盖。
  3) 归一与过滤：统一小写；黑名单噪声（mirror/videos/views/api/drive/customer service 等）；频次阈值≥20；别名合并（semantic_terms.aliases）。
  4) 词库兜底：优先用 semantic_terms 标注为品牌的词/别名统计；未收录高频词先入 semantic_candidates，人工审核后再入榜。
  5) 修复后重算品牌榜：提及量 + 平均分 + 痛点占比，用于雷达/对比。

## 4) 当前可用成果
- 社区×痛点热力：可直接用于看板/优先分析。
- 品牌榜：正式用“评论口径品牌榜”（见下），帖子口径仅作补充参考。

## 5) 已执行修复与新的实体榜（基于 content_entities 映射修正）
- 操作：将 content_entities.content_type='post' 的 content_id 从 posts_hot.id 映射并更新为 posts_raw.id（source+source_post_id 对齐），更新 17,240 条；评论侧实体未改。
- 映射后基于 content_entities 的品牌榜（黑名单去噪，频次≥20；平均分主要来自帖子，pain 占比低因帖子未打 pain 标签、评论实体覆盖不足）：
  - amazon 5,413 / 平均分 25.9 / 痛点占比 28.1%
  - shopify 1,573 / 7.4 / 0.0%
  - aliexpress 1,023 / 41.5 / 0.0%
  - paypal 768 / 8.2 / 0.0%
  - tiktok 723 / 5.2 / 0.0%
  - walmart 553 / 41.4 / 0.0%
  - etsy 545 / 58.9 / 0.0%
  - ebay 453 / 33.3 / 0.0%
  - meta 449 / 30.6 / 0.0%
  - google 438 / 12.5 / 0.0%
  - facebook 418 / 22.7 / 0.0%
  - instagram 309 / 5.3 / 0.0%
  - youtube 269 / 12.9 / 0.0%
  - chatgpt 265 / 5.0 / 0.0%
  - target 252 / 21.4 / 0.0%
  - ugc 218 / 11.3 / 0.0%
  - conversion rate 206 / 43.1 / 0.0%
  - sku 204 / 3.8 / 0.0%
  - software 193 / 64.0 / 0.0%
  - usps 190 / 15.2 / 0.0%
- 说明：pain 占比仍低，原因是帖子未打 pain 标签且评论实体覆盖不足；需执行评论实体抽取和（如需）帖子 pain 标签后再重算品牌×痛点。

## 6) 品牌榜（修复后，推荐用评论口径；去噪，小写，频次≥10）
- 评论口径品牌榜（提及 / 均分 / 痛点占比，黑名单去噪）：
  - amazon 1,440 / 2.6 / 4.4%
  - walmart 326 / 5.5 / 2.8%
  - shopify 279 / 1.3 / 2.9%
  - discord 202 / 1.0 / 3.5%
  - aliexpress 187 / 2.7 / 4.3%
  - etsy 160 / 4.0 / 3.1%
  - meta 149 / 1.6 / 3.4%
  - google 119 / 1.9 / 1.7%
  - ups 91 / 2.8 / 6.6%
  - paypal 88 / 2.2 / 25.0%
  - facebook 83 / 2.0 / 1.2%
  - ebay 72 / 2.7 / 1.4%
  - target 64 / 4.2 / 3.1%
  - usps 53 / 4.5 / 13.2%
  - youtube 46 / 3.5 / 6.5%
  - tiktok 45 / 8.6 / 8.9%
  - instagram 27 / 1.8 / 0.0%
  - apple 25 / 2.3 / 4.0%
  - software 24 / 3.7 / 0.0%
  - vat 23 / 1.9 / 0.0%
  - temu 21 / 4.0 / 0.0%
  - chatgpt 21 / 5.5 / 0.0%
  - alibaba 11 / 1.8 / 0.0%
  - ...（详表可按同口径导出）
- 帖子口径（频次≥20，去噪）可作为补充，用于提及量/均分，不建议用其 pain%（帖子未打 pain 时为0）。
