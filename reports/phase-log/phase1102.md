# phase1102 - Hotpost 探索回流 R10/R11 落地

## 这轮达到的目的
把 Hotpost 探索社区池接成显式试采入口和 `community_pool` 回流 dry-run。

## 当前状态变化
- R10 已落地：日常采集默认不含探索社区，`probe_community_discovery.py --scope ...` 才显式开启探索试采。
- R11 已落地：新增只读回流 dry-run，不写 DB、不自动入池、标签从 `community_interest_tags.json` 映射。
- 当前 dry-run 结果：`input_rows=16 / already_in_pool=3 / keep_testing=13 / promote_candidate=0 / reject=0`。
- 新产物：`reports/community-governance/community-pool-feedback-dry-run-2026-05-08.{json,md}`。

## 还没完成什么
- 还没有真实 probe 产出的候选 / 草稿 / 发布证据。
- 当前没有社区满足进入 R12 Dev 写入闸门。

## 下一步做什么
先人工看 dry-run；若要继续，选择具体 scope 跑显式 probe，产生证据后再重跑 R11。
