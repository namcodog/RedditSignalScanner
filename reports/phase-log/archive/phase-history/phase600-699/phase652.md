# Phase 652 - Suggestion 直达 Group Draft

## 结果

这轮把 `breakdown suggestion` 又往前推了一步：

- 不再只是“看候选”
- 现在可以直接从 suggestion 一键 seed 成 group draft

也就是说，运营后续不需要再手工复制 `candidate_ids` 去组拆解卡了。

## 代码落点

- `backend/app/api/v1/endpoints/hotpost_card_review.py`
- `backend/app/schemas/hotpost_card_review.py`
- `backend/app/services/hotpost/breakdown_candidate_clusterer.py`
- `backend/tests/api/test_hotpost_breakdown_seed.py`

## 新增能力

新增接口：

- `POST /api/hotpost/card-review/seed-draft-from-suggestion`

请求体：

```json
{
  "suggestion_id": "suggestion-ecommerce-sellers-ac0954d331",
  "card_type": "write"
}
```

行为：

- 根据 `suggestion_id` 找到对应的 candidate 组
- 直接复用现有 grouped draft builder
- 自动走内容生成器
- 保存到 draft 列表

## 验证

定向测试：

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/api/test_hotpost_breakdown_seed.py \
  backend/tests/api/test_hotpost_card_review.py \
  backend/tests/services/hotpost/test_breakdown_candidate_clusterer.py -q
```

结果：`5 passed`

运行态烟雾验证：

- `openapi.json` 已能看到 `/api/hotpost/card-review/seed-draft-from-suggestion`
- 对空 body 调接口返回 `422`，说明新路由已挂到 8006 运行态

## 当前判断

这轮之后，`breakdown supply` 的 V1 已经从：

- auto suggestion

推进到：

- auto suggestion
- one-click seed draft
- human review
- publish

也就是说，“拆解”这条链现在已经不是概念流，而是半自动运营流。
