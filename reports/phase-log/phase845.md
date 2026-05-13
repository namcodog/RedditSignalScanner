# phase845

## 时间
- 2026-04-16

## 主题
- 按新发布口径一次性补齐昨日 `business-growth-ops` backlog，并完成展示链同步

## 这轮判断

- 用户要的是“一次性把昨天该发的补齐”，不是先发一小批试水。
- 当前 backlog 最重、最明确的一段在 `business-growth-ops`，所以本轮先把这一段一次性清完。
- 当前明确不该发的只有两张：
  - `draft-cand-business-growth-ops-1sinaiq-validate`
    - 旧 `hot`，freshness 不成立
  - `draft-group-business-growth-ops-d2d62644cb`
    - growth purity cleanup 已判定退出的旧 organic 位

## 这轮变化

- 先发 `3` 张 growth 卡：
  - `card-cand-business-growth-ops-1sm2jgu-validate`
  - `card-group-business-growth-ops-0128e96117`
  - `card-group-business-growth-ops-8b853663bf`
- 随后一次性连续发布剩余 `business-growth-ops` backlog：
  - `13` 张 `breakdown`
- 本轮合计新增发布：
  - `16` 张
- `published_count`：
  - `203 -> 216`

## 展示链同步

- 最新 release：
  - `release-c12a58160973`
- 当前状态：
  - `card_count = 216`
  - `feed_contract = 30/30`
  - `cloud_db copy guard = ok`

## 运行时问题与修复

- 发布后暴露的真实问题不是内容没发成，而是 `push_mini_snapshot` 在“无新增 hot，只新增 signal/breakdown”的场景下会重复重刷全部 `hot controversy`，导致展示链收口变慢。
- 已修复：
  - `backend/app/services/hotpost/mini_snapshot.py`
    - 当所有 `hot validate` 卡都已带齐 `controversy_chart / controversy_meta` 时，跳过重复刷新
  - 测试：
    - `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`
- 回归：
  - `7 passed`

## 当前状态

- “昨天的卡没补完”这个问题，当前在 `business-growth-ops` 已经收口。
- 当前发布面和展示链都已经同步到新 release，不再停留在 `published` 层。

## 下一步

1. 继续按 `value-threshold publishing` 处理剩余 scope backlog。
2. 不为补量硬发旧 `hot`。
3. 默认先看 freshness、价值阈值和展示链收口速度。
