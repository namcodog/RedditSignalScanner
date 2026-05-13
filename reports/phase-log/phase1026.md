# phase1026 - Hotpost V13 title-standalone 回灌

1. 这轮达到的目的
   - 将 V13 “title 可独立理解”规则回灌到 Hotpost 生产 prompt 资产、`card_content_rules.yaml` 和可切换 LLM profile。

2. 当前状态变化
   - `title` 现在被明确约束为微摘要：保留对象、变化/冲突和核心意思，不靠 `summary_line` 才能看懂。
   - 已新增 `hotpost_v13_title_standalone` profile：`deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro`，默认不启用。
   - 未接入 V13 实验脚本，未新增生产实时 repair pass，未改字段/schema/历史卡片。

3. 还没完成什么
   - 没有生成 `production-after-v13-title-backfill` 报告；本仓库未找到现成生产 after-v13 回归脚本。

4. 下一步做什么
   - 如要验收真实输出质感，应另取非 V12/V13 原样本，用该 profile 跑 shadow/backfill 包给人工审核。
