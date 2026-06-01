# Hotpost Semantic Brief Precheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Hotpost V13 出卡链路升级成“结构化 semantic brief -> writer -> AI 预检 -> 人工 review”的可验证链路。

**Architecture:** 不重写现有 V13 主链，只在两个位置补强：先让 semantic brief 输出更硬的结构化合同，再在 `generate_card_content()` 生成 draft 后增加 AI precheck。第一版 precheck 只做 report-only，不自动发布、不自动改稿；后续再打开 rewrite。

**Tech Stack:** Python, Pydantic-style schema dict, pytest, existing OpenAI-compatible LLM client, Hotpost card draft/candidate stores.

---

## File Structure

- Modify: `backend/app/services/hotpost/card_content_generator.py`
  - 扩展 semantic brief schema。
  - 在生成 draft 后调用 precheck。
- Create: `backend/app/services/hotpost/draft_precheck.py`
  - 定义 precheck 输入、schema、结果解析、阻断/重写判断。
- Create: `backend/app/services/hotpost/draft_precheck_store.py`
  - 把 precheck 结果写到 `reports/hotpost-draft-precheck/`，先 report-only。
- Modify: `backend/app/services/hotpost/review_card_ops.py`
  - `seed_review_draft_from_candidate()` 保存 draft 后同时保存 precheck 报告。
- Modify: `backend/scripts/hotpost/review_cards.py`
  - `show-draft` 输出附带 precheck summary。
- Test: `backend/tests/services/hotpost/test_card_content_generator_semantic_brief.py`
- Test: `backend/tests/services/hotpost/test_draft_precheck.py`
- Test: `backend/tests/scripts/hotpost/test_review_cards_precheck.py`

---

## Success Criteria

- semantic brief 新增字段可由 schema 验证。
- writer prompt 能收到新增结构化字段。
- draft precheck 能输出 `PASS / REWRITE / BLOCK`。
- 第一版不自动拦截发布，只在 `show-draft` 和报告里提示。
- 所有新增逻辑可用 fake LLM client 测试，不依赖真实模型。
- 现有测试 `test_reddit_search_spec_builder.py` 和 card content 相关测试通过。

---

### Task 1: Strengthen Semantic Brief Schema

**Files:**
- Modify: `backend/app/services/hotpost/card_content_generator.py`
- Test: `backend/tests/services/hotpost/test_card_content_generator_semantic_brief.py`

- [ ] **Step 1: Write failing schema test**

Add a test that calls `_semantic_brief_json_schema()` and asserts these new fields exist:

```python
def test_semantic_brief_schema_has_quality_contract_fields() -> None:
    from app.services.hotpost.card_content_generator import _semantic_brief_json_schema

    schema = _semantic_brief_json_schema()
    props = schema["properties"]

    assert props["confidence_level"]["enum"] == ["high", "medium", "low"]
    assert props["publish_risk"]["enum"] == ["pass", "needs_human_review", "block"]
    assert props["claim_type"]["enum"] == [
        "channel_test",
        "market_validation",
        "tool_adoption",
        "platform_risk",
        "generic_advice",
        "unknown",
    ]
    assert "evidence_strength" in props
    assert "writer_constraints" in props
    assert "confidence_level" in schema["required"]
    assert "publish_risk" in schema["required"]
```

- [ ] **Step 2: Run failing test**

Run:

```bash
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_card_content_generator_semantic_brief.py -q
```

Expected: fail because the new fields do not exist.

- [ ] **Step 3: Extend `_semantic_brief_json_schema()`**

Add these fields:

```python
"confidence_level": {
    "type": "STRING",
    "enum": ["high", "medium", "low"],
},
"publish_risk": {
    "type": "STRING",
    "enum": ["pass", "needs_human_review", "block"],
},
"claim_type": {
    "type": "STRING",
    "enum": [
        "channel_test",
        "market_validation",
        "tool_adoption",
        "platform_risk",
        "generic_advice",
        "unknown",
    ],
},
"evidence_strength": {
    "type": "OBJECT",
    "properties": {
        "quote_support": {"type": "STRING", "enum": ["strong", "partial", "weak"]},
        "single_thread_risk": {"type": "BOOLEAN"},
        "has_specific_user_action": {"type": "BOOLEAN"},
        "has_measurable_result": {"type": "BOOLEAN"},
    },
    "required": [
        "quote_support",
        "single_thread_risk",
        "has_specific_user_action",
        "has_measurable_result",
    ],
},
"writer_constraints": {
    "type": "OBJECT",
    "properties": {
        "must_not_claim": {"type": "ARRAY", "items": {"type": "STRING"}},
        "must_downscope": {"type": "ARRAY", "items": {"type": "STRING"}},
        "preferred_angle": {"type": "STRING"},
    },
    "required": ["must_not_claim", "must_downscope", "preferred_angle"],
},
```

Also append the new keys to the schema `required` list.

- [ ] **Step 4: Update semantic brief system prompt**

In `_generate_profile_semantic_brief()`, add explicit instructions:

```text
confidence_level 只能是 high / medium / low。
publish_risk 只能是 pass / needs_human_review / block；证据弱、单帖风险高、泛建议时不要写 pass。
claim_type 必须选择最贴近的一个；如果只是泛创业建议，写 generic_advice。
evidence_strength 要判断 quote 是否真支撑主张、是否单帖、是否有具体动作、是否有可量化结果。
writer_constraints 负责告诉后续 writer 必须降调和不能写什么。
```

- [ ] **Step 5: Verify test passes**

Run:

```bash
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_card_content_generator_semantic_brief.py -q
```

Expected: pass.

---

### Task 2: Add Draft Precheck Node

**Files:**
- Create: `backend/app/services/hotpost/draft_precheck.py`
- Test: `backend/tests/services/hotpost/test_draft_precheck.py`

- [ ] **Step 1: Write failing tests**

Create tests for three decisions:

```python
def test_parse_precheck_pass() -> None:
    from app.services.hotpost.draft_precheck import parse_draft_precheck_result

    result = parse_draft_precheck_result({
        "decision": "PASS",
        "reasons": [],
        "field_issues": [],
        "risk_flags": [],
        "suggested_patches": {},
    })

    assert result["decision"] == "PASS"
    assert result["blocks_publish"] is False


def test_parse_precheck_rewrite() -> None:
    from app.services.hotpost.draft_precheck import parse_draft_precheck_result

    result = parse_draft_precheck_result({
        "decision": "REWRITE",
        "reasons": ["summary overclaims evidence"],
        "field_issues": [{"field": "summary_line", "issue": "overclaim"}],
        "risk_flags": ["overclaim"],
        "suggested_patches": {"summary_line": "评论区开始把问题指向渠道心智。"},
    })

    assert result["decision"] == "REWRITE"
    assert result["blocks_publish"] is False


def test_parse_precheck_block() -> None:
    from app.services.hotpost.draft_precheck import parse_draft_precheck_result

    result = parse_draft_precheck_result({
        "decision": "BLOCK",
        "reasons": ["quote does not support claim"],
        "field_issues": [{"field": "title", "issue": "unsupported"}],
        "risk_flags": ["unsupported_claim"],
        "suggested_patches": {},
    })

    assert result["decision"] == "BLOCK"
    assert result["blocks_publish"] is True
```

- [ ] **Step 2: Implement parser and schema**

Create `draft_precheck.py` with:

```python
from __future__ import annotations

from typing import Any


PRECHECK_DECISIONS = {"PASS", "REWRITE", "BLOCK"}


def draft_precheck_json_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "decision": {"type": "STRING", "enum": ["PASS", "REWRITE", "BLOCK"]},
            "reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
            "field_issues": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "field": {"type": "STRING"},
                        "issue": {"type": "STRING"},
                    },
                    "required": ["field", "issue"],
                },
            },
            "risk_flags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "suggested_patches": {"type": "OBJECT"},
        },
        "required": ["decision", "reasons", "field_issues", "risk_flags", "suggested_patches"],
    }


def parse_draft_precheck_result(payload: dict[str, Any]) -> dict[str, Any]:
    decision = str(payload.get("decision") or "").strip().upper()
    if decision not in PRECHECK_DECISIONS:
        decision = "REWRITE"
    return {
        "decision": decision,
        "blocks_publish": decision == "BLOCK",
        "reasons": [str(item) for item in list(payload.get("reasons") or []) if str(item).strip()],
        "field_issues": list(payload.get("field_issues") or []),
        "risk_flags": [str(item) for item in list(payload.get("risk_flags") or []) if str(item).strip()],
        "suggested_patches": dict(payload.get("suggested_patches") or {}),
    }
```

- [ ] **Step 3: Add prompt builder**

Add:

```python
def build_draft_precheck_messages(*, draft_payload: dict[str, Any], semantic_brief: dict[str, Any] | None) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是 Hotpost 发布前 AI 预检节点。只判断草稿是否忠于证据，不润色正文。"
                "输出 JSON。decision 只能是 PASS、REWRITE、BLOCK。"
                "PASS 表示可以进入人工 review；REWRITE 表示字段有问题但可修；BLOCK 表示证据不支撑或明显不该发。"
                "重点检查 title、summary_line、why_now、audience、detail 是否夸大、跑题、模板腔、残缺英文、quote 不支撑。"
                "不要新增事实，不要替人工发布。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "semantic_brief": semantic_brief or {},
                    "draft": draft_payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]
```

Remember to import `json`.

- [ ] **Step 4: Run tests**

Run:

```bash
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_draft_precheck.py -q
```

Expected: pass.

---

### Task 3: Wire Precheck Into Generation, Report-Only

**Files:**
- Modify: `backend/app/services/hotpost/card_content_generator.py`
- Create: `backend/app/services/hotpost/draft_precheck_store.py`
- Test: `backend/tests/services/hotpost/test_card_content_generator_precheck.py`

- [ ] **Step 1: Add result carrier**

Because current draft schemas should not be widened yet, store precheck outside draft JSON. Create `draft_precheck_store.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[4] / "reports" / "hotpost-draft-precheck"


def draft_precheck_path(draft_id: str) -> Path:
    safe = "".join(ch for ch in draft_id if ch.isalnum() or ch in {"-", "_"})
    return _ROOT / f"{safe}.json"


def save_draft_precheck(draft_id: str, payload: dict[str, Any]) -> Path:
    path = draft_precheck_path(draft_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_draft_precheck(draft_id: str) -> dict[str, Any] | None:
    path = draft_precheck_path(draft_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Add precheck call after writer output**

In `card_content_generator.py`, after `finalize_validation_readout(...)`, call `_generate_draft_precheck(...)` only if production profile exists. Keep report-only:

```python
precheck_result = None
if production_profile is not None and isinstance(signal_draft, ValidationCardDraft):
    precheck_result = await _generate_draft_precheck(
        signal_draft,
        semantic_brief=semantic_brief,
        model=signal_model,
        timeout=signal_timeout,
        client_factory=client_factory,
    )
    setattr(signal_draft, "_hotpost_precheck_result", precheck_result)
```

- [ ] **Step 3: Implement `_generate_draft_precheck()`**

Use existing `_generate_json()`:

```python
async def _generate_draft_precheck(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    semantic_brief: dict[str, Any] | None,
    model: str,
    timeout: float,
    client_factory: LLMClientFactory,
) -> dict[str, Any]:
    from app.services.hotpost.draft_precheck import (
        build_draft_precheck_messages,
        draft_precheck_json_schema,
        parse_draft_precheck_result,
    )

    payload = await _generate_json(
        model=model,
        timeout=timeout,
        messages=build_draft_precheck_messages(
            draft_payload=draft.model_dump(mode="json"),
            semantic_brief=semantic_brief,
        ),
        client_factory=client_factory,
        max_tokens=1200,
        response_schema=draft_precheck_json_schema(),
        trace_id=draft.draft_id,
        stage="draft_precheck",
    )
    return parse_draft_precheck_result(payload)
```

- [ ] **Step 4: Persist precheck in review ops**

In `review_card_ops.py`, after `generated = await generate_card_content(seeded)`, check:

```python
precheck_result = getattr(generated, "_hotpost_precheck_result", None)
if isinstance(precheck_result, dict):
    from app.services.hotpost.draft_precheck_store import save_draft_precheck
    save_draft_precheck(generated.draft_id, precheck_result)
```

Keep this before `_save_or_replace_draft(generated)`.

- [ ] **Step 5: Test with fake client**

Write a test using a fake `client_factory` that returns valid JSON for semantic brief, writer payload, and precheck payload. Assert that `_hotpost_precheck_result["decision"] == "PASS"`.

- [ ] **Step 6: Run tests**

Run:

```bash
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_card_content_generator_precheck.py -q
```

Expected: pass.

---

### Task 4: Show Precheck in Review CLI

**Files:**
- Modify: `backend/scripts/hotpost/review_cards.py`
- Test: `backend/tests/scripts/hotpost/test_review_cards_precheck.py`

- [ ] **Step 1: Modify `_review_payload()`**

Add:

```python
from app.services.hotpost.draft_precheck_store import load_draft_precheck
```

Then:

```python
def _review_payload(draft: ValidationCardDraft | WritingCardDraft) -> dict:
    payload = draft.model_dump(mode="json")
    precheck = load_draft_precheck(draft.draft_id)
    if precheck is not None:
        payload["precheck"] = precheck
    return payload
```

- [ ] **Step 2: Add CLI test**

Test that `_review_payload()` includes `precheck` when a report exists. Use a temporary monkeypatched store path if needed.

- [ ] **Step 3: Run targeted test**

Run:

```bash
PYTHONPATH=backend pytest backend/tests/scripts/hotpost/test_review_cards_precheck.py -q
```

Expected: pass.

---

### Task 5: Add Report-Only Ops Contract

**Files:**
- Modify: `docs/sop/2026-04-08-评审与发布SOP.md`
- Modify: `docs/sop/2026-04-08-日常产卡SOP.md`

- [ ] **Step 1: Document precheck semantics**

Add this rule:

```markdown
### AI 预检节点

- `draft_precheck` 是人工 review 前的 report-only 节点。
- 第一版不自动发布、不自动拒绝、不自动改稿。
- `PASS`：可以进入人工 review。
- `REWRITE`：人工优先看 `field_issues / suggested_patches`，必要时 update draft。
- `BLOCK`：默认不发，除非人工明确说明证据为什么仍足够。
- precheck 结果保存在 `reports/hotpost-draft-precheck/<draft_id>.json`。
```

- [ ] **Step 2: Run doc grep**

Run:

```bash
rg "draft_precheck|AI 预检" docs/sop
```

Expected: both SOP files mention the new node.

---

### Task 6: Verification and Commit

- [ ] **Step 1: Run all targeted tests**

Run:

```bash
PYTHONPATH=backend pytest \
  backend/tests/services/hotpost/test_card_content_generator_semantic_brief.py \
  backend/tests/services/hotpost/test_draft_precheck.py \
  backend/tests/services/hotpost/test_card_content_generator_precheck.py \
  backend/tests/scripts/hotpost/test_review_cards_precheck.py \
  -q
```

Expected: all pass.

- [ ] **Step 2: Run existing guard tests**

Run:

```bash
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py -q
```

Expected: `17 passed`.

- [ ] **Step 3: Manual dry-run**

Seed one known candidate in a dev-safe context:

```bash
PYTHONPATH=backend python backend/scripts/hotpost/review_cards.py show-draft <draft_id>
```

Expected: JSON output includes `precheck`.

- [ ] **Step 4: Commit**

```bash
git add \
  backend/app/services/hotpost/card_content_generator.py \
  backend/app/services/hotpost/draft_precheck.py \
  backend/app/services/hotpost/draft_precheck_store.py \
  backend/app/services/hotpost/review_card_ops.py \
  backend/scripts/hotpost/review_cards.py \
  backend/tests/services/hotpost/test_card_content_generator_semantic_brief.py \
  backend/tests/services/hotpost/test_draft_precheck.py \
  backend/tests/services/hotpost/test_card_content_generator_precheck.py \
  backend/tests/scripts/hotpost/test_review_cards_precheck.py \
  docs/sop/2026-04-08-日常产卡SOP.md \
  docs/sop/2026-04-08-评审与发布SOP.md

git commit -m "feat(hotpost): add draft precheck node"
```

---

## Rollout Plan

1. First release: report-only. Do not block publish.
2. Observe 3-5 daily operations.
3. Count `PASS / REWRITE / BLOCK` and compare with human decisions.
4. Only after calibration, allow:
   - `BLOCK` to hide from default review queue.
   - `REWRITE` to trigger one automatic repair attempt.
5. Never allow precheck to auto-publish.

## Risks

- Extra model call increases latency and timeout exposure.
- Precheck may over-block novel but valid cards.
- If semantic brief confidence is wrong, writer and precheck may share the same blind spot.

Mitigation:

- First version report-only.
- Use current writer model for precheck, no new provider.
- Keep human override.
- Persist every precheck result for audit.
