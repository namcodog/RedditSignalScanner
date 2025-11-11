# 领域抓取时效与策略参数（crawler.yml 指南）

用途：为 `backend/config/crawler.yml` 的 tier 策略提供可读配置指南；便于按领域/优先级设定窗口、排序混合与回补策略。

| domain | time_window | sort_mix(top/new/hot) | re_crawl_frequency | hot_cache_ttl | notes |
|---|---|---|---|---|---|
| 跨境选品 (what_to_sell) | 30d | 0.50 / 0.30 / 0.20 | T1=2h / T2=6h / T3=24h | 24h | 重视历史热帖与新品增长；必要时 7d 热点回补 |
| 营销/运营 (how_to_sell) | 30d | 0.40 / 0.40 / 0.20 | T1=2h / T2=6h / T3=24h | 24h | 新帖能带来玩法变化，new 权重略高 |
| 市场/渠道 (where_to_sell) | 30d | 0.60 / 0.20 / 0.20 | T1=2h / T2=6h / T3=24h | 24h | 平台口碑波动慢，top 权重更高 |
| 供应链/合规/物流 (how_to_source) | 30d | 0.45 / 0.35 / 0.20 | T1=2h / T2=6h / T3=24h | 24h | 事件性波动存在，适度 new/hot 混合 |

补充策略：
- 空集回退：若某层过滤后为空，回退为“不过滤 priority”，并记录警告（已实现）。
- 热点回补：当近 7 日存在高 upvotes 的代表帖，触发额外 7d 新帖抓取一轮（上限 N）。
- 区域权重（可选）：按 market=NA/EU/SEA 细分社区集，where_to_sell 层对目标区域提高 top/new 权重。
- 增量水位：`watermark_enabled=true`、`watermark_grace_hours=4`，避免短时重复抓取。

落地：将上述表中参数转写进 `backend/config/crawler.yml` 的 tiers（T1/T2/T3），并用 `make crawler-dryrun` 校验摘要输出。

