from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from app.schemas.analysis import AnalysisRead


@dataclass(slots=True, frozen=True)
class ControlledSummaryWorkflowDeps:
    build_context: Callable[..., Any] | None
    render_report: Callable[..., str] | None


@dataclass(slots=True, frozen=True)
class ControlledSummaryWorkflowResult:
    markdown: str | None
    metrics_data: dict[str, Any]

    def as_tuple(self) -> tuple[str | None, dict[str, Any]]:
        return self.markdown, dict(self.metrics_data)


def _candidate_paths(path: Path) -> list[Path]:
    if path.is_absolute():
        return [path]
    parts = path.parts
    if parts and parts[0] == "backend":
        return [path, Path(*parts[1:])]
    return [path, Path("backend") / path]


def _first_existing(path: Path) -> Path | None:
    for candidate in _candidate_paths(path):
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue
    return None


def _load_json_file(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def render_controlled_summary_workflow(
    *,
    analysis_payload: AnalysisRead,
    task_id: UUID,
    blocked_by_quality_gate: bool,
    deps: ControlledSummaryWorkflowDeps,
) -> ControlledSummaryWorkflowResult:
    if blocked_by_quality_gate or not deps.build_context or not deps.render_report:
        return ControlledSummaryWorkflowResult(markdown=None, metrics_data={})

    try:
        analysis_dict = {
            "insights": analysis_payload.insights.model_dump(mode="json"),
            "sources": analysis_payload.sources.model_dump(mode="json"),
        }

        lex_path = _first_existing(
            Path(
                os.getenv(
                    "SEMANTIC_LEXICON_PATH",
                    "backend/config/semantic_sets/crossborder_v2.1.yml",
                )
            )
        )
        metrics_path = _first_existing(
            Path(
                os.getenv(
                    "SEMANTIC_METRICS_PATH",
                    "backend/reports/local-acceptance/metrics/metrics.json",
                )
            )
        )
        template_path = _first_existing(
            Path("backend/config/report_templates/executive_summary_v2.md")
        )
        if template_path is None or not template_path.exists():
            return ControlledSummaryWorkflowResult(markdown=None, metrics_data={})

        lex_data = _load_json_file(lex_path)
        metrics_data = _load_json_file(metrics_path)
        ctx, _ = deps.build_context(
            analysis_dict,
            lex_data,
            metrics_data,
            task_id=str(task_id),
        )
        markdown = deps.render_report(
            template_path.read_text(encoding="utf-8"),
            ctx,
        )
        return ControlledSummaryWorkflowResult(
            markdown=markdown,
            metrics_data=metrics_data,
        )
    except Exception:
        return ControlledSummaryWorkflowResult(markdown=None, metrics_data={})


__all__ = [
    "ControlledSummaryWorkflowDeps",
    "ControlledSummaryWorkflowResult",
    "render_controlled_summary_workflow",
]
