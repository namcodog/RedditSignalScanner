# Phase 676 - Breakdown V2 Auto-Materialize Landed

## 本阶段结论

`breakdown V2` 已经完成。

这次真正落地的不是新的 prompt，而是把拆解供给从：

- `suggestion -> 人工 seed-group -> draft`

推进成：

- `suggestion -> 自动 materialize write draft -> 人工 review -> publish`

自动化止于 `draft`，人工 `publish` 保留。

## 本阶段完成

### 1. 新增 breakdown materialize 主链

- 新增服务：
  - `backend/app/services/hotpost/breakdown_draft_materializer.py`
- 新增 API：
  - `POST /api/hotpost/card-review/materialize-drafts`
- 新增 CLI：
  - `backend/scripts/hotpost/materialize_breakdown_drafts.py`

### 2. 自动化边界收紧

- 只接受最终仍为 `write` 的结果
- 不允许静默降成 `validate`
- draft/card 已存在时跳过
- 不自动 publish

### 3. 真实 suggestion 已验证

当前真实 suggestion：

- `suggestion-ai-automation-94bfe667d1`

第一次执行：

- `materialized = 1`
- 落下真实 `write draft`

第二次执行：

- `skipped_existing = 1`
- 证明自动去重生效

## 关键验证

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_breakdown_draft_materializer.py \
  backend/tests/api/test_hotpost_breakdown_seed.py \
  backend/tests/services/hotpost/test_breakdown_candidate_clusterer.py \
  backend/tests/services/hotpost/test_card_content_generator.py -q
```

结果：`19 passed`

真实执行：

```bash
PYTHONPATH=backend python backend/scripts/hotpost/materialize_breakdown_drafts.py
```

第一次结果：

- `materialized = 1`

第二次结果：

- `skipped_existing = 1`

## 当前稳定资产

- 全局 signal 基线：
  - `human_summary_tight_why_now_v1`
- pack 专用写法：
  - `paid_econ_signal_readout_v2`
  - `selection_signal_readout_v1`
  - `agent_builder_signal_readout_v1`
- `signal judge`
- `signal input quality gate`
- `breakdown suggestion`
- `breakdown auto materialize`

## 下一步

V2 这条线不再继续补主链。

后续回到日常运行态：

1. 继续正常 collect / 产出 `📡 信号`
2. 有合格 suggestion 时，跑 materialize 生成待审 `🔍 拆解 draft`
3. 人工 review 后 publish

如果后面再开新题，应单独立项：

- `breakdown skill optimization`
- 或更自动化的 workflow trigger/SOP
