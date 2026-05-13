# phase910

1. 这轮达到的目的
   把 `small-goods` 补卡从“口头说只改配置”真正落实成“只调 YAML profile、真实 collect、真实发布、真实同步”。

2. 当前状态变化
   `selection-30d-small-goods-demand / tail` 已按补卡合同收紧：去掉 `homeowners / ApartmentHacks / onebag` 这类会放大 listing 噪音的社区，`tail` 的 `candidate_cap` 也从 `4` 降到 `3`，明确退回“长尾探索配角”。按新配置重跑后，`demand=20`、`tail=12`，并已真实补发 `3` 张 `small-goods` 卡：`1se4i3o`（玻璃保鲜盒平替）、`1scp4vn`（多功能清洁小工具）、`1rzx6t5`（差旅非包类小物）。最新发布真相源是 `release-f772e56df334`，小程序快照同步到 `release-be57ce64ac15`，同步检查通过。

3. 还没完成什么
   `small-goods` 这条线已经重新补起来了，但 `ManyBaggers / CleaningTips` 仍会天然带一些 listing 噪音；当前只是把它压到可用，不是已经做到全自动无噪声。

4. 下一步做什么
   接下来继续沿这套新 profile 补 `small-goods`，优先盯三类：平替/材质切换、清洁工具清单、长尾社区的非主流小物判断；后续只继续改 YAML，不回头改硬规则。
