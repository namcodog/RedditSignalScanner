# Mainline Mini-Inspired Slimming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep mainline deep analysis intact while slimming the heaviest collection/readiness path by turning existing readiness/remediation support modules into the single truth source for `analysis_engine.py` wrappers.

**Architecture:** This is not a new shallow scanner and not a UI project. It borrows the mini app's product mechanism: thin entrypoints, explicit gates, single truth sources, and read-only artifacts. The first implementation slice keeps existing private wrapper names in `analysis_engine.py`, but delegates their bodies to `analysis_readiness_support.py` and `analysis_remediation_support.py`.

**Tech Stack:** Python 3.11, pytest, FastAPI service modules, existing `analysis_*_support.py` helpers.

---

## Boundaries

Do not touch:

- `hotpost-mini/hotpost-mini-app`
- `backend/data/hotpost/mini_snapshots`
- `hotpost-mini/.../cloudfunctions/*/data`
- Hotpost candidates / drafts / releases
- `frontend/`
- DB migrations
- `ReportService` decoupling

This plan is separate from daily Hotpost operations and root `task_plan.md`.

## Files

- Modify: `backend/app/services/analysis/analysis_engine.py`
- Create: `backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py`
- Read-only verification: `backend/tests/services/analysis/test_analysis_readiness_support.py`
- Read-only verification: `backend/tests/services/analysis/test_analysis_remediation_support.py`

## Task 1: Lock Engine Readiness Delegation Tests

**Files:**
- Create: `backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py`

- [ ] **Step 1: Create failing delegation tests**

Create `backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest

from app.schemas.task import TaskSummary
from app.services.analysis import sample_guard
from app.services.analysis import analysis_engine
from app.services.analysis.topic_profiles import TopicProfile


@dataclass(slots=True)
class _FakeArtifacts:
    insights: dict[str, Any]
    sources: dict[str, Any]
    report_html: str
    action_items: list[dict[str, Any]]
    confidence_score: float


def _task_summary() -> TaskSummary:
    now = datetime(2026, 5, 7, tzinfo=timezone.utc)
    return TaskSummary(
        id="00000000-0000-0000-0000-000000000001",
        user_id=None,
        status="processing",
        product_description="PayPal fee and payout risk scanner",
        mode="market_insight",
        audit_level="lab",
        topic_profile_id="paypal_v1",
        membership_level=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
        retry_count=0,
        failure_category=None,
    )


def _topic_profile() -> TopicProfile:
    return TopicProfile(
        id="paypal_v1",
        topic_name="PayPal",
        product_desc="PayPal fee and payout risk scanner",
        vertical="payments",
        mode="market_insight",
        allowed_communities=["r/paypal"],
        community_patterns=[],
        required_entities_any=[],
        soft_required_entities_any=[],
        include_keywords_any=[],
        exclude_keywords_any=[],
    )


@pytest.mark.asyncio
async def test_engine_sample_guard_delegates_to_readiness_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    expected = sample_guard.SampleCheckResult(
        hot_count=1,
        cold_count=2,
        combined_count=3,
        shortfall=4,
        remaining_shortfall=0,
        supplemented=False,
        supplement_posts=[],
    )

    async def fake_run_sample_guard_check(**kwargs: Any) -> sample_guard.SampleCheckResult:
        calls.update(kwargs)
        return expected

    monkeypatch.setattr(
        analysis_engine.readiness_support,
        "run_sample_guard_check",
        fake_run_sample_guard_check,
    )

    result = await analysis_engine._run_sample_guard(
        ["paypal"],
        "PayPal seller risk",
        lookback_days=30,
    )

    assert result == expected
    assert calls["keywords"] == ["paypal"]
    assert calls["product_description"] == "PayPal seller risk"
    assert calls["lookback_days"] == 30
    assert calls["min_sample_size"] == analysis_engine.MIN_SAMPLE_SIZE


@pytest.mark.asyncio
async def test_engine_data_readiness_snapshot_delegates_to_readiness_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _topic_profile()
    calls: dict[str, Any] = {}

    async def fake_build_data_readiness_snapshot(**kwargs: Any) -> dict[str, Any]:
        calls.update(kwargs)
        return {"communities_total": 1, "status_counts": {"ACTIVE": 1}}

    monkeypatch.setattr(
        analysis_engine.readiness_support,
        "build_data_readiness_snapshot",
        fake_build_data_readiness_snapshot,
    )

    result = await analysis_engine._build_data_readiness_snapshot(topic_profile=profile)

    assert result == {"communities_total": 1, "status_counts": {"ACTIVE": 1}}
    assert calls["topic_profile"] is profile
    assert calls["session_factory"] is analysis_engine.SessionFactory


def test_engine_insufficient_sample_result_delegates_to_readiness_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _task_summary()
    sample_result = sample_guard.SampleCheckResult(
        hot_count=1,
        cold_count=1,
        combined_count=2,
        shortfall=10,
        remaining_shortfall=8,
        supplemented=True,
        supplement_posts=[{"id": "p1"}],
    )

    def fake_build_insufficient_sample_artifacts(**kwargs: Any) -> _FakeArtifacts:
        assert kwargs["task"] is task
        assert kwargs["sample_result"] is sample_result
        assert kwargs["lookback_days"] == 90
        assert kwargs["min_sample_size"] == analysis_engine.MIN_SAMPLE_SIZE
        return _FakeArtifacts(
            insights={"pain_points": []},
            sources={"analysis_blocked": "insufficient_samples"},
            report_html="<html>blocked</html>",
            action_items=[],
            confidence_score=0.0,
        )

    monkeypatch.setattr(
        analysis_engine.readiness_support,
        "build_insufficient_sample_artifacts",
        fake_build_insufficient_sample_artifacts,
    )

    result = analysis_engine._build_insufficient_sample_result(
        task,
        sample_result,
        lookback_days=90,
    )

    assert result.insights == {"pain_points": []}
    assert result.sources == {"analysis_blocked": "insufficient_samples"}
    assert result.report_html == "<html>blocked</html>"
    assert result.action_items == []
    assert result.confidence_score == 0.0


@pytest.mark.asyncio
async def test_engine_auto_backfill_delegates_to_remediation_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _task_summary()
    profile = _topic_profile()
    calls: dict[str, Any] = {}

    async def fake_schedule_auto_backfill_for_insufficient_samples(**kwargs: Any) -> list[dict[str, Any]]:
        calls.update(kwargs)
        return [{"type": "backfill_posts", "targets": 2}]

    monkeypatch.setattr(
        analysis_engine.remediation_support,
        "schedule_auto_backfill_for_insufficient_samples",
        fake_schedule_auto_backfill_for_insufficient_samples,
    )

    result = await analysis_engine._schedule_auto_backfill_for_insufficient_samples(
        task=task,
        topic_profile=profile,
        keywords=["paypal"],
    )

    assert result == [{"type": "backfill_posts", "targets": 2}]
    assert calls["task"] is task
    assert calls["topic_profile"] is profile
    assert calls["keywords"] == ["paypal"]
    assert calls["select_top_communities_fn"] is analysis_engine._select_top_communities
```

- [ ] **Step 2: Run the new tests and verify they fail before implementation**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py
```

Expected before implementation: failure because `analysis_engine.readiness_support` and `analysis_engine.remediation_support` are not imported module aliases yet, or wrappers do not delegate.

## Task 2: Delegate Engine Readiness Wrappers

**Files:**
- Modify: `backend/app/services/analysis/analysis_engine.py`

- [ ] **Step 1: Add support module imports**

In `backend/app/services/analysis/analysis_engine.py`, add imports near other analysis imports:

```python
from app.services.analysis import analysis_readiness_support as readiness_support
from app.services.analysis import analysis_remediation_support as remediation_support
```

- [ ] **Step 2: Replace `_run_sample_guard` body with thin delegation**

Change `_run_sample_guard(...)` to:

```python
async def _run_sample_guard(
    keywords: Sequence[str],
    product_description: str,
    *,
    lookback_days: int,
) -> Optional[sample_guard.SampleCheckResult]:
    supplement = partial(
        _supplement_samples,
        product_description=product_description,
    )
    return await readiness_support.run_sample_guard_check(
        keywords=keywords,
        product_description=product_description,
        lookback_days=max(1, int(lookback_days)),
        min_sample_size=MIN_SAMPLE_SIZE,
        hot_fetcher=_fetch_hot_samples,
        cold_fetcher=_fetch_cold_samples,
        supplementer=supplement,
    )
```

- [ ] **Step 3: Replace `_build_data_readiness_snapshot` body with thin delegation**

Change `_build_data_readiness_snapshot(...)` to:

```python
async def _build_data_readiness_snapshot(
    *, topic_profile: TopicProfile
) -> dict[str, Any]:
    return await readiness_support.build_data_readiness_snapshot(
        topic_profile=topic_profile,
        session_factory=SessionFactory,
    )
```

- [ ] **Step 4: Replace `_build_insufficient_sample_result` body with thin delegation**

Change `_build_insufficient_sample_result(...)` to:

```python
def _build_insufficient_sample_result(
    task: TaskSummary,
    sample_result: sample_guard.SampleCheckResult,
    *,
    lookback_days: int,
) -> AnalysisResult:
    artifacts = readiness_support.build_insufficient_sample_artifacts(
        task=task,
        sample_result=sample_result,
        lookback_days=lookback_days,
        min_sample_size=MIN_SAMPLE_SIZE,
    )
    return AnalysisResult(
        insights=artifacts.insights,
        sources=artifacts.sources,
        report_html=artifacts.report_html,
        action_items=artifacts.action_items,
        confidence_score=artifacts.confidence_score,
    )
```

- [ ] **Step 5: Replace `_schedule_auto_backfill_for_insufficient_samples` body with thin delegation**

Change `_schedule_auto_backfill_for_insufficient_samples(...)` to:

```python
async def _schedule_auto_backfill_for_insufficient_samples(
    *,
    task: TaskSummary,
    topic_profile: "TopicProfile | None",
    keywords: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    return await remediation_support.schedule_auto_backfill_for_insufficient_samples(
        task=task,
        topic_profile=topic_profile,
        keywords=keywords,
        select_top_communities_fn=_select_top_communities,
    )
```

- [ ] **Step 6: Remove imports that become unused only if tests confirm**

After replacing the bodies, remove only imports that become unused because of this task. Do not clean unrelated imports.

## Task 3: Verify The First Slimming Slice

**Files:**
- Read-only verification

- [ ] **Step 1: Run delegation tests**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py
```

Expected: all tests pass.

- [ ] **Step 2: Run existing support tests**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/analysis/test_analysis_readiness_support.py backend/tests/services/analysis/test_analysis_remediation_support.py
```

Expected: existing support tests pass.

- [ ] **Step 3: Run analysis engine target tests**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/analysis/test_analysis_engine.py backend/tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py
```

Expected: existing engine behavior remains compatible.

- [ ] **Step 4: Run mainline backend smoke**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/api/test_analyze.py backend/tests/api/test_reports.py backend/tests/services/report/test_report_service.py backend/tests/services/analysis/test_analysis_engine.py
```

Expected: same baseline class as audit, previously `70 passed, 1 skipped`.

- [ ] **Step 5: Run frontend contract smoke**

Run:

```bash
cd frontend && npm test -- --run src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/ReportFlow.integration.test.tsx src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts
```

Expected: same baseline class as audit, previously `27 passed`.

- [ ] **Step 6: Verify boundary**

Run:

```bash
make boundary-status
git -C hotpost-mini/hotpost-mini-app status --short
git diff --check -- backend/app/services/analysis/analysis_engine.py backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py
```

Expected:

- mini repo remains clean
- no whitespace errors

## Task 4: Update Audit / Progress Notes

**Files:**
- Modify: `reports/audits/mainline-reset-audit-2026-05-06.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] **Step 1: Add implementation note to audit**

Append under `Recommended Next Moves`:

```markdown
2026-05-07 first slimming slice: `analysis_engine.py` readiness/remediation wrappers now delegate to existing support modules. This preserves deep analysis while reducing duplicated preflight ownership.
```

- [ ] **Step 2: Add progress entry**

Add a concise `progress.md` entry:

```markdown
- 已完成主项目瘦身第一刀：没有降低分析深度，只把 `analysis_engine.py` 中 readiness / insufficient sample / remediation 的重复主逻辑收回已有 support 模块。
```

- [ ] **Step 3: Add finding**

Add a concise `findings.md` entry:

```markdown
- 小程序可借鉴的是产品机制，不是分析深度。主项目第一刀应借“单一真相源 / gate / artifact”的机制，把已有 support 模块变成真实边界。
```

- [ ] **Step 4: Final diff check**

Run:

```bash
git diff --check -- reports/audits/mainline-reset-audit-2026-05-06.md progress.md findings.md
```

Expected: no output.

## Self Review

- This plan does not create a shallow scanner.
- This plan does not touch Hotpost daily operations or mini app product state.
- This plan uses existing support modules instead of creating a parallel system.
- This plan preserves current private wrapper names to avoid breaking old tests.
- This plan directly addresses the heavy collection/readiness route without reducing report depth.
