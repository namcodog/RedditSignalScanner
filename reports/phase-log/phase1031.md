# phase1031

## 这轮达到的目的

V13 title 规则新增“主体 + 业务场景”约束，解决标题只写“移动端/转化率/会话回放”但不交代谁的场景的问题。

## 当前状态变化

已更新 V13 检测器、真实 prompt assets、few-shot 和 `card_content_rules.yaml`，相关回归 `158 passed`。Shopify 单卡 shadow 标题已补成“Shopify 卖家移动端转化率卡在 2.1%...”。新增 batch004 shadow `20/20` 成功，title issues `0`，density issues `0`。

## 还没完成什么

本轮仍是 shadow 报告，未写回历史已发布卡。batch004 中出现 OpenRouter 上游 deepseek 临时 `429`，脚本重试后恢复，但全量跑仍需小批次推进。

## 下一步做什么

人工审核 `reports/evals/hotpost_v13_title_subject_fullrun_batch004_20_w2.md`；若认可，继续按 `20` 张一批、`workers=2` 分批跑完整已发布卡 shadow 包。
