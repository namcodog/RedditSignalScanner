# phase890

1. 这轮达到的目的
- 把“字段不完整仍在 draft/review 才挡”这条尾项前移到 publish surface 编排阶段。

2. 当前状态变化
- 新增 `draft_surface_readiness.py`。
- `offline_publish_plan`、`review_queue_policy`、`review_card_ops` 已按字段完整性过滤/替换脏 draft。
- 当前脏 draft `draft-cand-business-growth-ops-1sokcov-validate` 被识别为 `detail_fields_incomplete`，且不再算 `ready_validate_drafts`。

3. 还没完成什么
- 这次只收掉了“脏 draft 占 gate 名额”的浪费。
- 薄 pack / 新节点能否继续把真实可发布供给做厚，还要看后续 live collect 和 release 验证。

4. 下一步做什么
- 继续按分层 gate 跟后续 release，重点看薄 pack / 新节点能否在 `stable` 下持续进发布面。
