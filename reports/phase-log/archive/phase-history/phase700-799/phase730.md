# Phase 730

## 本轮目标

继续提高 `hot` 供给密度，不放松门禁；验证扩充 YAML 后，`listing` 面和 `hot` 面是否真正抬起来。

## 实现

### 1. 扩 `hot` 供给密度（只改 YAML）

文件：
- `backend/config/hotpost_supply_discovery_v2.yaml`

主要改动：
- AI
  - `key-people-and-route` 改为 `mixed + allow_listing`
  - 补 `listing_communities: [OpenAI, singularity, MachineLearning, artificial]`
  - `ai-product-and-adoption` 补 listing 面
  - `upstream-winds` 提高 `candidate_cap` 与 `listing_subreddit_limit`
- 增长
  - `ads / creator-affiliate-distribution / content-production-and-editorial` 补 listing 社区和 listing 规则
  - `paid-economics / organic-discovery` 提高 `candidate_cap` 与 `listing_subreddit_limit`
- 电商
  - `seller-category-direction / unit-economics-and-platform-risk` 补 `shopify / sidehustle`
  - `category-winds / kill-signals` 提高 `candidate_cap` 与 `listing_subreddit_limit`

### 2. 热点 judge 再补一刀

文件：
- `backend/app/services/hotpost/card_lane_policy.py`
- `backend/app/services/hotpost/hotpost_supply_contract.py`

改动：
- `sustained` 老帖不再一刀全砍
- 只放回“超高热度 + 超高评论”的持续热点：
  - `sustained_override_min_score = 500`
  - `sustained_override_min_comments = 150`

## 验证

- `pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py backend/tests/services/hotpost/test_source_scope_catalog.py -q`
  - `18 passed`
- `pytest backend/tests/services/hotpost/test_card_lane_policy.py -q`
  - `11 passed`
- `py_compile`
  - 通过

### 重跑 collect

- `python backend/scripts/hotpost/daily_collect.py --scope ai-automation --max-candidates 24`
  - `{"ai-automation": 24}`
- `python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --max-candidates 24`
  - `{"business-growth-ops": 23}`
- `python backend/scripts/hotpost/daily_collect.py --scope ecommerce-sellers --max-candidates 24`
  - `{"ecommerce-sellers": 20}`

### 审计结果

运行：
- `python backend/scripts/hotpost/audit_hot_lane.py`

结果：
- `candidate_total: 67`
- `listing_total: 22`（上一轮是 `14`）
- `runtime_hot_total: 2`
- `runtime_signal_listing_total: 20`

当前 runtime hot 仍是：
- `cand-ai-automation-1sg0kpp` / `r/OpenAI`
- `cand-ai-automation-1sftdkl` / `r/OpenAI`

## 结论

- 这轮已经证明：`hot` 的**供给密度**确实抬起来了，`listing_total` 从 `14 -> 22`。
- 但 `runtime_hot_total` 仍然停在 `2`，说明当前瓶颈已经不是“面太窄”，而是：
  - 这些新增 listing 候选里，真正像 `hot` 的比例还不够高
  - `growth / ecommerce` 目前更多还是高信息 signal，不是争议型 hot

## 下一步

下一步不该继续盲目扩所有 listing，而应该更聚焦地补：
- AI：路线争论 / 人物观点冲突
- 增长：GEO / SEO / Ads 的路线分歧与平台争议
- 电商：卖家群体报数 / 平台政策 / 费用争议

也就是说：
**供给面已经开始变厚；下一步要提高的是“listing 里真热点的占比”。**
