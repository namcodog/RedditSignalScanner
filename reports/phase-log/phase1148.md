# phase1148 - Hotpost V13 结构化 brief 与 AI 预检节点落地

## 这轮达到的目的
- 把 V13 出卡链路从 `semantic_brief -> writer -> 人工 review` 升级为 `semantic_brief -> writer -> draft_precheck -> 人工 review`。

## 当前状态变化
- `semantic_brief` 已新增 `confidence_level / publish_risk / claim_type / evidence_strength / writer_constraints`，节点 1 到节点 2 的数据传递变成可机读合同。
- `draft_precheck` 已接入生产出卡链路，输出 `PASS / REWRITE / BLOCK`；结果只做 report-only，保存到 `reports/hotpost-draft-precheck/<draft_id>.json`，`show-draft` 会展示。
- 审计补齐两个缺口：breakdown/write 最终稿不会丢预检；预检超时或异常会转成 `REWRITE + precheck_error`，不打断出卡主链。

## 还没完成什么
- 预检目前不自动改稿、不自动发布，也不改变 queue 排序；人工 review 仍是最终决策点。
- 下一轮真实出卡需要观察 `PASS / REWRITE / BLOCK` 的分布和误判样本。

## 下一步做什么
- 在下一次 V13 seed / review 时抽样看 precheck 是否能提前拦住放大证据、泛建议和弱主张。
- 如果 `REWRITE / BLOCK` 稳定有效，再考虑是否接入 review queue 默认展示或批量审核摘要。
