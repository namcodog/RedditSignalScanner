# phase961

## 这轮达到的目的
- 继续深挖 `4月22日` 当天卡池，并把最近几天真实打出来但尚未正式接线的新社区补进发现配置。

## 当前状态变化
- `ecommerce-sellers` 新增 `paper-goods-and-gifting` 集群，正式接入 `stationery / planners / Journaling / hobonichi / fountainpens / GiftIdeas`。
- `business-growth-ops` 的 `funnel-conversion` 正式接入 `consulting / sales`，并把 bridge limit 从 `8` 放到 `10`，保证新社区不会被截断。
- runtime spec 回归测试已通过：`PYTHONPATH=backend pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py -q` -> `15 passed`。
- 新一轮 collect 后，`ecommerce-sellers` 的 `publishable_total` 从 `0` 抬到 `6`，`business-growth-ops` 从 `2` 抬到 `8`。
- 这轮又新落成 `3` 张 draft：`draft-group-ecommerce-sellers-66c5bba7b9-validate`、`draft-group-ecommerce-sellers-307a8f00af-validate`、`draft-cand-business-growth-ops-1ss0drr-validate`。

## 还没完成什么
- 新接入的 `stationery / ManyBaggers` 已经开始出候选，但这轮仍被 `single_thread_weak_evidence / no_substantive_quotes` 挡住，暂时没转成硬卡。
- `consulting / sales` 已吃进 runtime spec，但这轮 collect 还没真正打出对应候选。

## 下一步做什么
- 先按今天主池重排总数，确认这轮新增后可审卡面有多少。
- 再继续优先看新社区候选，只有确认 `7D` 真的没有净新增时，才继续扩 `15D`。
