# Phase 650 - Breakdown Suggestion V1 落地

## 结果

`breakdown supply` 合同已经完成第一阶段落地：

- 新增 `breakdown suggestion` 自动聚合层
- 新增只读接口：
  - `/api/hotpost/card-review/suggestions`
- 仍保留人工发布闸门

这意味着：

- 系统开始自动发现“哪些 signal 值得合成拆解”
- 但不会自动把拆解卡发出去

## 代码落点

- `backend/app/services/hotpost/breakdown_candidate_clusterer.py`
- `backend/app/schemas/hotpost_card_review.py`
- `backend/app/api/v1/endpoints/hotpost_card_review.py`
- `backend/tests/api/test_hotpost_card_review.py`

## 当前行为

V1 suggestion 规则是保守的：

- 同 `source_scope_id`
- 同 `topic_pack_id`
- 至少 2 条 candidate
- 至少 2 个帖子
- 至少 2 条 quote
- 自动产出：
  - `candidate_ids`
  - `evidence_score`
  - `hypothesis`
  - `reason_codes`

## 验证

定向测试：

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/api/test_hotpost_card_review.py \
  backend/tests/api/test_hotpost_card_candidates.py -q
```

结果：`9 passed`

运行态验证：

- 已重启 8006
- `GET /api/hotpost/card-review/suggestions?limit=10` 已返回 6 条 suggestion

## 当前判断

这轮已经把“拆解供给机制”从概念变成了可操作接口。

但 V1 仍然只是保守 heuristics：

- suggestion 能出
- 不代表每条 suggestion 都应该直接 seed-group / publish

后续真正值钱的工作，不是再把自动化做重，而是：

- 审 suggestion 质量
- 再决定要不要进入自动 seed-group
