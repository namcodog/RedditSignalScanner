# phase1042

## 这轮达到的目的

完成 V13 production route 审计验收，区分“默认路由已接入”和“完整 V13 优化器是否等价落地”。

## 当前状态变化

确认正式 `generate_card_content()` 会通过 `production_profile_id=hotpost_v13_title_standalone` 走 `deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro`；正式 seed/review 入口会吃到这条链路。hot 热议图仍独立，读取 `hot_controversy` 配置。

## 还没完成什么

V13 eval/shadow 里的 `find_v13_title_issues()` 与 `repair_title_independence()` 没有完整进入生产代码；所以本轮只能验收“V13 profile 默认路由”，不能验收“V13 完整优化结果 100% 覆盖生产”。

## 下一步做什么

如要满验收，需要把 V13 title issue detector + title-only repair 抽成生产服务模块，并让 `generate_card_content()` 在 writer 后执行检测与最多两轮 title-only repair。
