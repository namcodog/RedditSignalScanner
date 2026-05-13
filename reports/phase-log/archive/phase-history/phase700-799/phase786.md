# phase786

## 事项

- 把 `L2 homepage_hot_first_breakdown_floor_dedup_v1` 回灌到桌面项目首页货架
- 只改首页货架调度，不改单卡文案、不改 lane 定义、不改 schema

## 本次改动

- 更新首页快照构建：
  - `backend/app/services/hotpost/mini_snapshot.py`
- 更新供给目标：
  - `backend/config/hotpost_supply_discovery_v2.yaml`
- 增补首页货架测试：
  - `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`

## 实际回灌的 3 条规则

- 首卡优先 `hot`
- 前 `30` 张里 `breakdown >= 5`
- 前 `30` 张里去掉同一 `source_link + lane` 的重复占位

## 没改的边界

- 没有改 `signal / hot / breakdown` prompt
- 没有改 lane 定义
- 没有改收藏 / 登录 / 详情页
- 没有改 mini snapshot schema
- `card_selection_policy.py` 这轮未动

## 验证

- `pytest backend/tests/scripts/hotpost/test_push_mini_snapshot.py -q --tb=short -p no:schemathesis`
- `pytest backend/tests/services/hotpost/test_hot_detail_contract.py -q --tb=short -p no:schemathesis`
- `python3 backend/scripts/hotpost/push_mini_snapshot.py --skip-bundle`

## 结果

- 新 release：`release-6a9985bd4b5d`
- `card_count = 155`
- `feed_contract = 30/30`
- 首页首卡：`hot`
- 前 `30` 张里：`breakdown = 5`
- 前 `30` 张里：无同一 `source_link + lane` 重复

## 结论

- `L2 homepage shelf mix v1` 已按最短路径回灌到桌面项目
- 当前首页货架已达到：
  - 首卡承担 `近期爆帖`
  - `breakdown` 保底出现
  - 同源同 lane 不再占两个首页位
