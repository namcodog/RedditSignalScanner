from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Any, Awaitable, Callable, Protocol

from app.schemas.analysis import AnalysisRead
from app.services.report.report_brief_builder import build_narrative_report_brief
from app.services.report.content_guardrails import contains_meta_leak, contains_systemy_copy
from app.services.report.report_markdown_contract import (
    validate_narrative_markdown_against_canonical,
)

logger = logging.getLogger(__name__)

_REQUIRED_REPORT_HEADINGS = (
    "## 1. 开篇概览",
    "## 2. 决策风向标",
    "## 3. 概览（市场健康度诊断）",
    "## 4. 核心战场推荐（画像分级）",
    "## 5. 用户痛点拆解",
    "## 6. 关键决策驱动力",
    "## 7. 商业机会",
)

_FORBIDDEN_REPORT_FRAGMENTS = (
    "## 已分析赛道（Analyzed Niche）",
    "### 卡片 1：需求趋势",
    "SaaS founders think",
    "Suggestions to",
    "would love",
    "趋势可用于继续决策",
    "结论已形成可读结构",
    "痛点销售比",
    "立即投放",
    "测试广告",
    "先验证",
    "案例切入",
    "payout帖",
)


class NarrativeReportClient(Protocol):
    async def generate(
        self,
        prompt: str | list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        ...


@dataclass(slots=True)
class NarrativeReportWorkflowInput:
    task: Any
    analysis: AnalysisRead
    blocked_by_quality_gate: bool
    inline_llm_enabled: bool


@dataclass(slots=True)
class NarrativeReportWorkflowDeps:
    enable_llm_summary: bool
    llm_model_name: str
    openai_api_key: str
    format_facts: Callable[[Any], str]
    build_prompt: Callable[[str, str], str | list[dict[str, str]]]
    client_factory: Callable[[str, str], NarrativeReportClient]


def _strip_markdown_fence(raw: str) -> str:
    text = (raw or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if not lines:
        return text
    # Remove opening fence and optional language tag.
    body = lines[1:] if lines[0].startswith("```") else lines
    if body and body[-1].strip() == "```":
        body = body[:-1]
    return "\n".join(body).strip()


def _build_facts_payload(
    *,
    report_structured: dict[str, Any],
    facts_slice: Any,
    format_facts: Callable[[Any], str],
) -> str:
    brief_payload = build_narrative_report_brief(
        report_structured=report_structured,
        facts_slice=facts_slice,
    )
    if not facts_slice:
        formatted_facts = "facts_slice unavailable"
    else:
        try:
            formatted_facts = format_facts(facts_slice)
        except Exception:
            formatted_facts = str(facts_slice)

    return (
        "【report_brief】\n"
        f"{brief_payload}\n\n"
        "【compact_facts】\n"
        f"{formatted_facts}\n"
    )


def _is_valid_narrative_markdown(
    markdown: str,
    *,
    report_structured: dict[str, Any],
) -> bool:
    text = (markdown or "").strip()
    if not text:
        return False
    if any(heading not in text for heading in _REQUIRED_REPORT_HEADINGS):
        return False
    if any(fragment in text for fragment in _FORBIDDEN_REPORT_FRAGMENTS):
        return False
    if validate_narrative_markdown_against_canonical(
        markdown=text,
        report_structured=report_structured,
    ):
        return False
    return not contains_meta_leak(text) and not contains_systemy_copy(text)


async def run_narrative_report_workflow(
    *,
    workflow_input: NarrativeReportWorkflowInput,
    deps: NarrativeReportWorkflowDeps,
) ->Optional[ tuple[str], bool]:
    report_structured = workflow_input.analysis.sources.report_structured
    if (
        not report_structured
        or workflow_input.blocked_by_quality_gate
    ):
        return None, False

    model_name = str(deps.llm_model_name or "").strip()
    api_key = str(deps.openai_api_key or "").strip()
    if (
        not deps.enable_llm_summary
        or model_name == "local-extractive"
        or not api_key
    ):
        return None, False

    try:
        product_description = (
            str(workflow_input.analysis.sources.product_description or "").strip()
            or str(getattr(workflow_input.task, "product_description", "") or "").strip()
            or "市场洞察"
        )
        facts_payload = _build_facts_payload(
            report_structured=report_structured,
            facts_slice=workflow_input.analysis.sources.facts_slice,
            format_facts=deps.format_facts,
        )
        prompt = deps.build_prompt(product_description, facts_payload)
        client = deps.client_factory(model_name, api_key)
        raw = await client.generate(prompt, max_tokens=7000, temperature=0.25)
        markdown = _strip_markdown_fence(raw)
        if not markdown:
            return None, False
        if not markdown.lstrip().startswith("#"):
            markdown = f"# {product_description} · 市场洞察报告\n\n{markdown}"
        if not _is_valid_narrative_markdown(
            markdown,
            report_structured=report_structured,
        ):
            logger.info("narrative report rejected by markdown contract")
            return None, False
        return markdown, True
    except Exception:
        logger.warning("narrative report generation failed", exc_info=True)
        return None, False


__all__ = [
    "NarrativeReportClient",
    "NarrativeReportWorkflowDeps",
    "NarrativeReportWorkflowInput",
    "run_narrative_report_workflow",
]
