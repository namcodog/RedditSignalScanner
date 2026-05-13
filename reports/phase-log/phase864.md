# phase864

1. 这轮达到的目的
把“直到 value-threshold publishing 下新增收益耗尽再停”固定成默认发卡准则，不再按“先发几张”执行。

2. 当前状态变化
仓库默认入口新增 `make hotpost-publish-until-exhausted`；`run_intake_freshness_gate.py` 的帮助文案已改成一轮 `collect-until-exhausted -> sync -> plan -> gate cycle`；主项目 SOP、小程序发卡 SOP、以及 `hot / signal / breakdown` skills 已同步到同一口径。

3. 还没完成什么
微信侧还没导入最新 cloud_db 并重部署 `miniRelease`；freshest supply 还要继续验证连续 gain，不是单次恢复出卡就结束。

4. 下一步做什么
按新 workflow 继续发卡：有新增价值就继续 review / publish / rerun；没有新增价值再停；同时完成微信侧导入和部署。
