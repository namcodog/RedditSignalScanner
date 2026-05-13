# Phase 731

## 本轮目标

继续提高 `hot` 供给密度，并验证扩面后 `runtime_hot_total` 是否自然上涨。

## 实现

- 在 `hot` judge 里新增 `title_debate_terms`，让标题本身就带强争议/强警报的帖子可以进入 `hot` 判断。
- 继续保持规则在 YAML：
  - `backend/config/hotpost_supply_discovery_v2.yaml`
  - `backend/app/services/hotpost/hotpost_supply_contract.py`
  - `backend/app/services/hotpost/card_lane_policy.py`

## 验证

- `pytest backend/tests/services/hotpost/test_card_lane_policy.py -q`
  - `12 passed`
- `py_compile`
  - 通过
- collect 重跑：
  - `ai-automation = 24`
  - `business-growth-ops = 23`
  - `ecommerce-sellers = 20`

## 审计结果

- `candidate_total: 67`
- `listing_total: 22`
- `runtime_hot_total: 2`
- `runtime_signal_listing_total: 20`

当前 runtime hot 仍只有：
- `r/OpenAI`
- `r/OpenAI`

## 结论

- `hot` 的入口已经变厚，但 `runtime_hot_total` 没涨。
- 说明当前瓶颈已经不是“collect 面太窄”，而是：
  - 新增 listing 候选里，真正像 `hot` 的比例仍然不高
  - 扩面不能再泛泛继续，下一步必须转成“争论社区 / 争论题材”的定向补强

## 下一步

- 不再盲目扩所有 listing
- 直接收窄到更会长出争论帖的社区簇：
  - AI：`OpenAI / singularity / artificial / MachineLearning`
  - 增长：`SEO / bigseo / DigitalMarketing / PPC / FacebookAds / googleads / adops`
  - 电商：`AmazonSeller / FulfillmentByAmazon / shopify / ecommerce`
