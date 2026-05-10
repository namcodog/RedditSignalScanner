# Phase 732

## 本轮目标

把 `hot` 审计口径和运行时规则彻底对齐，先把热点线稳住，再继续补密度。

## 实现

- 修正 `hot` 审计：
  - `backend/app/services/hotpost/hot_lane_audit.py`
  - 不再只统计 `listing` 里的 `hot`，改成统计全部 runtime `hot`
  - 新增：
    - `runtime_hot_listing_total`
    - `runtime_hot_search_total`
- 收紧 `search -> hot`：
  - `backend/config/hotpost_supply_discovery_v2.yaml`
  - `backend/app/services/hotpost/hotpost_supply_projection.py`
  - `backend/app/services/hotpost/card_lane_policy.py`
  - 改成只有显式白名单 pack 才允许 `search-based hot`
- 当前白名单：
  - `upstream-winds`
  - `organic-discovery`
- 明确禁止 `search-based hot` 的 pack：
  - `selection-signals`
  - `tools-efficiency`
  - `agent-builder`

## 验证

- `pytest backend/tests/services/hotpost/test_card_lane_policy.py -q`
  - `14 passed`
- `python backend/scripts/hotpost/audit_hot_lane.py`
- `python backend/scripts/hotpost/review_cards.py queue --type validate --limit 20`

## 审计结果

- `candidate_total: 67`
- `listing_total: 22`
- `runtime_hot_total: 3`
- `runtime_hot_listing_total: 2`
- `runtime_hot_search_total: 1`
- `runtime_signal_listing_total: 20`
- `published_hot_total: 3`

当前 runtime `hot` 只剩：
- `r/OpenAI` / `upstream-winds` / `listing`
- `r/OpenAI` / `upstream-winds` / `listing`
- `r/DigitalMarketing` / `organic-discovery` / `search`

被打回 `signal` 的典型假热点：
- `r/knives`
- `r/onebag`
- `r/BuyItForLife`
- `r/ClaudeAI`
- `r/LocalLLaMA`

## 结论

- `hot` 这条线现在先稳住了：
  - 审计口径和 queue 一致
  - 假热点不再大面积混进来
  - 真正保留下来的 `hot` 已经更接近“争议焦点 + 讨论形状”
- 当前下一步不该再修 judge 大方向，而是继续补：
  - AI 路线争论
  - SEO / GEO / Ads 争论
  - 电商群体报数 / 路线分歧

## 下一步

1. 继续扩 `hot` 专用供给面，不再泛泛扩所有 listing。
2. 继续按 `hot-ops` 跑，观察 `runtime_hot_total` 能否从 `3` 稳定涨到 `5+`。
3. 在 `hot` 稳住的前提下，再继续拉升整体供卡吞吐。
