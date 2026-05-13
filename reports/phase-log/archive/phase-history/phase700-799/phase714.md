# phase714 - selection strategy judge v1 + ops run

## 本轮完成

- 新增 `选卡裁判`：
  - [backend/app/services/hotpost/card_selection_policy.py](../../backend/app/services/hotpost/card_selection_policy.py)
- `review_cards.py queue` 已接入：
  - 热点优先
  - 领域配比补量
  - `listing-first` 候选加权

## 测试

- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_card_selection_policy.py backend/tests/services/hotpost/test_card_lane_policy.py backend/tests/api/test_hotpost_clues.py -q`
- 结果：`16 passed`

## 真实运营结果

- 发布总数：`65 -> 67`
- 当前 release：`release-7f143faecc4b`
- lane 分布：
  - `signal = 64`
  - `hot = 3`
- scope 分布：
  - `ai-automation = 26`
  - `business-growth-ops = 25`
  - `ecommerce-sellers = 16`

## 新发布卡

1. `供应商一拖期，卖家先学会的不是安抚，而是别再把货压在同一个供货方身上。`
2. `想买一口能多用几年的锅，大家先怀疑的不是品牌，而是不粘涂层到底撑不撑得住。`

## 本轮边界

- 领域补量不能覆盖质量闸门
- 被 `signal input quality gate` 拦住的电商候选没有硬发
- 低价误单类偶发事故没有为了补量硬发

## 下一步

- 继续按 `选卡裁判` 跑 `signal-ops`
- 继续优先看 `listing-first`
- 目标：
  - 拉平电商占比
  - 继续观察 `爆贴热点` 能否稳定长出第 4、5 张
