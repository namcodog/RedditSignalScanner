from __future__ import annotations

import pytest

from app.services.analysis_engine import AnalysisResult
from app.tasks.analysis_task import _warmup_auto_rerun_needed


@pytest.mark.parametrize(
    "sources, expect",
    [
        (
            {
                "analysis_blocked": "insufficient_samples",
                "report_tier": "C_scouting",
                "remediation_actions": [{"type": "backfill_posts", "targets": 0}],
            },
            (False, ""),
        ),
        (
            {
                "analysis_blocked": "insufficient_samples",
                "report_tier": "C_scouting",
                "remediation_actions": [{"type": "backfill_posts", "targets": 2}],
            },
            (True, "insufficient_samples"),
        ),
        (
            {
                "analysis_blocked": "",
                "report_tier": "C_scouting",
                "remediation_actions": [{"type": "backfill_comments", "targets": 0}],
            },
            (False, ""),
        ),
        (
            {
                "analysis_blocked": "",
                "report_tier": "C_scouting",
                "remediation_actions": [{"type": "backfill_comments", "targets": 1}],
            },
            (True, "missing_comments"),
        ),
    ],
)
def test_warmup_auto_rerun_needed_ignores_zero_targets(
    sources: dict, expect: tuple[bool, str]
) -> None:
    result = AnalysisResult(  # type: ignore[arg-type]
        insights={},
        sources=sources,
        report_html="",
        action_items=[],
        confidence_score=0.0,
    )
    assert _warmup_auto_rerun_needed(result) == expect
