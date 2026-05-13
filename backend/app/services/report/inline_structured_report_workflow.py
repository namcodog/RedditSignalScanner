from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

from app.schemas.analysis import AnalysisRead

logger = logging.getLogger(__name__)


class InlineStructuredReportClient(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        ...


@dataclass(slots=True)
class InlineStructuredReportWorkflowInput:
    task: Any
    analysis: AnalysisRead
    blocked_by_quality_gate: bool
    inline_llm_enabled: bool


@dataclass(slots=True)
class InlineStructuredReportWorkflowDeps:
    enable_llm_summary: bool
    llm_model_name: str
    openai_api_key: str
    format_facts: Callable[[Any], str]
    build_prompt: Callable[[str, str], str]
    client_factory: Callable[[str, str], InlineStructuredReportClient]


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


async def run_inline_structured_report_workflow(
    *,
    workflow_input: InlineStructuredReportWorkflowInput,
    deps: InlineStructuredReportWorkflowDeps,
) -> dict[str, Any] | None:
    structured_report = workflow_input.analysis.sources.report_structured
    if (
        structured_report
        or not workflow_input.inline_llm_enabled
        or workflow_input.blocked_by_quality_gate
    ):
        return structured_report

    facts_slice = getattr(workflow_input.analysis.sources, "facts_slice", None)
    model_name = str(deps.llm_model_name or "").strip()
    api_key = str(deps.openai_api_key or "").strip()
    if (
        not facts_slice
        or not deps.enable_llm_summary
        or model_name == "local-extractive"
        or not api_key
    ):
        return None

    try:
        facts_text = deps.format_facts(facts_slice)
        prompt = deps.build_prompt(
            str(getattr(workflow_input.task, "product_description", "") or ""),
            facts_text,
        )
        client = deps.client_factory(model_name, api_key)
        raw = await client.generate(prompt, max_tokens=4000, temperature=0.25)
        return _extract_json_payload(raw)
    except Exception:
        logger.warning("inline structured report generation failed", exc_info=True)
        return None


__all__ = [
    "InlineStructuredReportClient",
    "InlineStructuredReportWorkflowDeps",
    "InlineStructuredReportWorkflowInput",
    "run_inline_structured_report_workflow",
]
