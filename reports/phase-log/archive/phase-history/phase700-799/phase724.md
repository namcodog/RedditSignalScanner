# Phase 724 - 增长线 YAML 扩面与实体层接线

## 本轮目标

- 继续补宽 `business-growth-ops` 的 YAML 供给面
- 不只补关键词，还把 `named_entities` 真正接进搜索面
- 扩到 `GEO / SEO / 推广 / 获取流量 / 内容制作 / 市场分析`

## 关键改动

- 扩充 [hotpost_supply_discovery_v2.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_supply_discovery_v2.yaml)
  - `seo-geo`：补 `TechSEO / seogrowth / GenEngineOptimization`、`Google Search Console / Ahrefs / Semrush / Google Discover / AI Overviews`
  - `ads`：补 `Google Ads / Meta Ads / TikTok Ads / Reddit Ads / Performance Max / Advantage+`
  - `attribution`：补 `Triple Whale / Northbeam / Hyros / GA4 / Segment / PostHog / Elevar / Mixpanel`
  - `creator-affiliate-distribution`：补 `Beehiiv / Substack / ConvertKit / Kit / PartnerStack / Impact / Refersion / LTK / ShopMy`
  - 新增 `content-production-and-editorial`
  - 新增 `market-intel-and-audience-research`
  - pack `bucket_priority` 把 `entity` 正式纳入抓取顺序

- 修改 [hotpost_supply_projection.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hotpost_supply_projection.py)
  - `named_entities` 不再只是写在 YAML 里
  - 现在会合并进 `entity` bucket，真实进入搜索 query 面

- 补测试：
  - [test_source_scope_catalog.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_source_scope_catalog.py)
  - [test_reddit_search_spec_builder.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_reddit_search_spec_builder.py)

## 当前覆盖数字

- `ai-automation`
  - `7` 个题材簇
  - `20` 个去重社区
  - `34` 个命名实体
  - `104` 条关键词
  - `8` 个模板 stem
- `ecommerce-sellers`
  - `9` 个题材簇
  - `31` 个去重社区
  - `11` 个命名实体
  - `110` 条关键词
  - `8` 个模板 stem
- `business-growth-ops`
  - `7` 个题材簇
  - `35` 个去重社区
  - `54` 个命名实体
  - `150` 条关键词
  - `22` 个模板 stem

## 结论

- 增长线不再只剩泛 `SEO/PPC`
- 实体层已经真正进了 query 面，不再是纸面配置
- 现在最该做的不是继续修文案，而是用这份新 YAML 重跑 collect，验证真实候选面有没有明显变宽

## 验证

- `pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py backend/tests/services/hotpost/test_source_scope_catalog.py -q`
  - `14 passed`
