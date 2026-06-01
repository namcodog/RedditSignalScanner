# Brand Intelligence Daily Sidecar

- date: `2026-05-18`
- blocks_publish: `false`
- auto_write_semantic_lexicon: `false`
- cards_scanned: `1028`
- brands_observed: `196`
- verified_brands: `15`
- new_brand_candidates: `0`
- noise_items: `17`
- system_evidence_brands: `117`
- db_writes: `false`

## Daily Operator Checklist

- 记录新增品牌候选和最高证据。
- 记录 verified 品牌和对应兴趣标签。
- 记录系统证据包是否可用，不阻塞出卡。
- 记录 rejected/noise 样本，不进入品牌池。
- 记录 DB 写入状态；默认只读或 dry-run。

## New Brand Candidates

- none

## Verified Brands

| Brand | Status | Mentions | Communities | Tags |
|---|---:|---:|---:|---|
| google | verified | 327 | 31 | 家居生活选品, 好物选品, 广告投放, SEO&GEO, AI工具与Agent, 卖家店铺运营, 内容营销创作 |
| shopify | verified | 129 | 9 | 广告投放, SEO&GEO, AI工具与Agent, 卖家店铺运营 |
| Amazon | verified | 95 | 17 | 家居生活选品, 好物选品, AI工具与Agent, 电商平台政策与风向, 卖家店铺运营 |
| etsy | verified | 75 | 5 | 好物选品, 卖家店铺运营 |
| fba | verified | 52 | 4 | AI工具与Agent, 卖家店铺运营 |
| ebay | verified | 51 | 5 | AI工具与Agent, 卖家店铺运营 |
| facebook | verified | 50 | 8 | 广告投放, SEO&GEO, 众筹与品牌启动 |
| youtube | verified | 21 | 11 | 家居生活选品, 广告投放, SEO&GEO, AI工具与Agent |
| tiktok | verified | 9 | 3 | 广告投放, 众筹与品牌启动, 卖家店铺运营 |
| TikTok Shop | verified | 9 | 3 | 广告投放, 众筹与品牌启动, 卖家店铺运营 |
| instagram | verified | 7 | 4 | 广告投放, SEO&GEO |
| Temu | verified | 7 | 3 | 好物选品, 卖家店铺运营 |
| walmart | verified | 4 | 2 | AI工具与Agent, 卖家店铺运营 |
| alibaba | verified | 3 | 2 | AI工具与Agent, 卖家店铺运营 |
| bigcommerce | verified | 3 | 2 | 卖家店铺运营 |

## Noise Items

| Brand | Status | Mentions | Communities | Tags |
|---|---:|---:|---:|---|
| Case | rejected | 60 | 30 | 家居生活选品, 好物选品, 广告投放, SEO&GEO, AI工具与Agent, 众筹与品牌启动, 卖家店铺运营, 内容营销创作 |
| Kind | rejected | 43 | 25 | 家居生活选品, 好物选品, 广告投放, SEO&GEO, AI工具与Agent, 众筹与品牌启动, 电商平台政策与风向, 卖家店铺运营 |
| Campaign | rejected | 37 | 9 | 广告投放, AI工具与Agent, 众筹与品牌启动, 卖家店铺运营 |
| Spot | rejected | 28 | 20 | 家居生活选品, 好物选品, 广告投放, SEO&GEO, AI工具与Agent, 众筹与品牌启动, 卖家店铺运营, 内容营销创作 |
| Action | rejected | 23 | 15 | 广告投放, AI工具与Agent, 众筹与品牌启动, 卖家店铺运营, 内容营销创作 |
| Material | rejected | 19 | 9 | 好物选品, SEO&GEO |
| Flow | rejected | 18 | 11 | 广告投放, SEO&GEO, AI工具与Agent, 卖家店铺运营 |
| Cross | rejected | 15 | 12 | 好物选品, 广告投放, AI工具与Agent, 卖家店铺运营 |
| Article | rejected | 13 | 11 | 家居生活选品, SEO&GEO, AI工具与Agent, 众筹与品牌启动, 内容营销创作 |
| Ratio | rejected | 13 | 8 | 好物选品, 广告投放, SEO&GEO, AI工具与Agent, 众筹与品牌启动 |
| Sharp | rejected | 11 | 5 | SEO&GEO, AI工具与Agent, 卖家店铺运营 |
| Engineer | rejected | 8 | 4 | 广告投放, SEO&GEO, AI工具与Agent |
| Primary | rejected | 8 | 5 | 好物选品, 广告投放, SEO&GEO |
| Route | rejected | 8 | 7 | 家居生活选品, 广告投放, AI工具与Agent, 卖家店铺运营 |
| Downstream | rejected | 7 | 4 | AI工具与Agent |
| Heart | rejected | 6 | 4 | 好物选品 |
| Mirror | rejected | 1 | 1 |  |

## Semantic Review Queue

| Brand | Action | Auto Apply | Tags |
|---|---|---:|---|
| google | review_for_semantic_lexicon | `false` | 家居生活选品, 好物选品, 广告投放, SEO&GEO, AI工具与Agent, 卖家店铺运营, 内容营销创作 |
| shopify | review_for_semantic_lexicon | `false` | 广告投放, SEO&GEO, AI工具与Agent, 卖家店铺运营 |
| Amazon | review_for_semantic_lexicon | `false` | 家居生活选品, 好物选品, AI工具与Agent, 电商平台政策与风向, 卖家店铺运营 |
| etsy | review_for_semantic_lexicon | `false` | 好物选品, 卖家店铺运营 |
| fba | review_for_semantic_lexicon | `false` | AI工具与Agent, 卖家店铺运营 |
| ebay | review_for_semantic_lexicon | `false` | AI工具与Agent, 卖家店铺运营 |
| facebook | review_for_semantic_lexicon | `false` | 广告投放, SEO&GEO, 众筹与品牌启动 |
| youtube | review_for_semantic_lexicon | `false` | 家居生活选品, 广告投放, SEO&GEO, AI工具与Agent |
| tiktok | review_for_semantic_lexicon | `false` | 广告投放, 众筹与品牌启动, 卖家店铺运营 |
| TikTok Shop | review_for_semantic_lexicon | `false` | 广告投放, 众筹与品牌启动, 卖家店铺运营 |
| instagram | review_for_semantic_lexicon | `false` | 广告投放, SEO&GEO |
| Temu | review_for_semantic_lexicon | `false` | 好物选品, 卖家店铺运营 |
| walmart | review_for_semantic_lexicon | `false` | AI工具与Agent, 卖家店铺运营 |
| alibaba | review_for_semantic_lexicon | `false` | AI工具与Agent, 卖家店铺运营 |
| bigcommerce | review_for_semantic_lexicon | `false` | 卖家店铺运营 |
