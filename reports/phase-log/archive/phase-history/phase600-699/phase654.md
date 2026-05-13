# Phase 654 - 修复 Suggestion / Breakdown 门槛错位

## 结果

这轮把 `breakdown supply` 里最关键的漏洞收掉了：

- `suggestion` 门槛已收严到与 `breakdown` 基本对齐
- 不再允许“看起来能拆，实际上只会降回信号”的 suggestion 出现在候选池里
- 同时堵住了一个更脏的问题：
  - 用户请求 `write`
  - 系统却静默落成 `validate`

现在不会再出现这种静默降级。

## 修复内容

### 1. 收严 suggestion 证据门槛

`breakdown_candidate_clusterer` 现在要求：

- 至少 2 条 candidate
- 至少 2 个帖子
- 至少 3 条有效 quote
- 且满足：
  - `community_count >= 2`
  - 或 `thread_count >= 3`

这意味着 suggestion 不再只是“值得试着组卡”，
而是更接近“真的有机会成为拆解”。

### 2. 堵住静默降级

`seed-draft-from-suggestion` / `seed-draft` 现在如果请求的是 `write`，
但生成器最后没能保住 `write`，会直接报错，不会再偷偷保存成 `validate`。

### 3. 清理误生成脏数据

把这轮实战验证里误落下来的 2 张 `validate group draft` 清掉了：

- `draft-group-ecommerce-sellers-ac0954d331`
- `draft-group-ai-automation-8f0a4a210e`

当前磁盘状态：

- `drafts = 0`

## 验证

定向测试：

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_breakdown_candidate_clusterer.py \
  backend/tests/api/test_hotpost_card_review.py \
  backend/tests/api/test_hotpost_breakdown_seed.py \
  backend/tests/api/test_hotpost_breakdown_thresholds.py -q
```

结果：`7 passed`

运行态验证：

```bash
GET /api/hotpost/card-review/suggestions?limit=10
```

结果：

- `count = 0`

说明当前线上真实候选还不够格进拆解池，系统不再制造假拆解预期。

## 当前判断

这次修复后，`breakdown suggestion` 的语义终于收正了：

- 没到拆解门槛，就不该出 suggestion
- 想发拆解，就必须先拿到够硬的多帖证据

这不是让拆解变少，而是让“拆解”这个标签不再失真。
