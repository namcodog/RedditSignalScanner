from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = PROJECT_ROOT / "backend" / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from local_acceptance import (  # type: ignore  # Module lives under backend/scripts
    AcceptanceSummary,
    StepResult,
    render_markdown_report,
    summarize_results,
    parse_args,
)


def _ts(minutes: int = 0) -> datetime:
    base = datetime(2025, 10, 27, 12, 0, tzinfo=timezone.utc)
    return base + timedelta(minutes=minutes)


def test_summarize_results_marks_success_only_when_all_pass() -> None:
    started = _ts()
    finished = _ts(5)
    steps = [
        StepResult(name="redis", success=True, detail="redis ok", duration=0.2),
        StepResult(name="celery", success=False, detail="no worker", duration=0.5),
    ]

    summary = summarize_results(steps, started_at=started, finished_at=finished)

    assert summary.total_steps == 2
    assert summary.success_steps == 1
    assert summary.failed_steps == 1
    assert summary.success is False
    assert summary.duration_seconds == pytest.approx(300.0, rel=1e-3)


def test_render_markdown_report_contains_step_details() -> None:
    summary = AcceptanceSummary(
        total_steps=2,
        success_steps=2,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=120.0,
        success=True,
        started_at=_ts(),
        finished_at=_ts(2),
    )
    steps = [
        StepResult(name="redis", success=True, detail="redis ok", duration=0.2),
        StepResult(name="backend", success=True, detail="healthz ok", duration=0.3),
    ]

    markdown = render_markdown_report(summary, steps, environment="local")

    assert "redis" in markdown
    assert "✅" in markdown
    assert "总耗时" in markdown
    assert "local" in markdown


def test_parse_args_supports_legacy_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Makefile 仍传递 --backend-url/-frontend-url/-redis-url/-environment 参数，需要保持兼容。"""

    for key in (
        "LOCAL_ACCEPTANCE_BACKEND",
        "LOCAL_ACCEPTANCE_FRONTEND",
        "LOCAL_ACCEPTANCE_REDIS",
        "LOCAL_ACCEPTANCE_ENV",
    ):
        monkeypatch.delenv(key, raising=False)

    args = parse_args(
        [
            "--backend-url",
            "http://backend.local:8006",
            "--frontend-url",
            "http://frontend.local:3006",
            "--redis-url",
            "redis://redis.local:6379/0",
            "--environment",
            "acceptance",
        ]
    )

    assert args.backend == "http://backend.local:8006"
    assert args.frontend == "http://frontend.local:3006"
    assert args.redis == "redis://redis.local:6379/0"
    assert args.environment == "acceptance"
