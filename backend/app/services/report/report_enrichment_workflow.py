from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from uuid import UUID

from app.core.config import settings
from app.schemas.analysis import AnalysisRead, OpportunityReportOut
from app.services.llm.normalizer import LocalDeterministicNormalizer
from app.services.llm.rag_conf_normalizer import (
    LocalRagConfidenceNormalizer,
    OpenAIRagConfidenceNormalizer,
)
from app.services.llm.summarizer import LocalExtractiveSummarizer
from app.services.report.opportunity_report import build_opportunity_reports

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportEnrichmentInput:
    analysis: AnalysisRead
    blocked_by_quality_gate: bool
    inline_llm_enabled: bool


@dataclass(slots=True)
class ReportEnrichmentResult:
    action_items: list[OpportunityReportOut]
    normalization_rate: float
    normalization_details: list[dict[str, Any]]


def _clone_action_item(
    base: OpportunityReportOut,
    **updates: Any,
) -> OpportunityReportOut:
    data = base.model_dump()
    data.update(updates)
    return OpportunityReportOut(**data)


def _build_normalizer_candidates(analysis: AnalysisRead) -> list[str]:
    candidates: list[str] = []
    try:
        for row in analysis.insights.entity_summary.brands or []:
            name = getattr(row, "name", None) or (
                row.get("name") if isinstance(row, dict) else None
            )
            if name:
                candidates.append(str(name))
    except Exception:
        pass
    for comp in analysis.insights.competitors or []:
        name = getattr(comp, "name", None)
        if name:
            candidates.append(str(name))
    try:
        dict_path = None
        for path in [
            Path("backend/config/entity_dictionary/crossborder_v2.csv"),
            Path("backend/config/entity_dictionary/crossborder_v2_balanced.csv"),
            Path("backend/config/entity_dictionary/crossborder_v2_conservative.csv"),
            Path("backend/config/entity_dictionary/crossborder_v2_aggressive.csv"),
        ]:
            if path.exists():
                dict_path = path
                break
        if dict_path is not None:
            with dict_path.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    canonical = (row.get("canonical") or "").strip()
                    if canonical:
                        candidates.append(canonical)
    except Exception:
        pass
    return sorted({candidate.strip(): None for candidate in candidates if candidate}.keys())


def _build_rag_normalizer(
    *,
    capped_candidates: Sequence[str],
) -> tuple[str, Any]:
    if (
        getattr(settings, "enable_llm_summary", True)
        and getattr(settings, "llm_model_name", "local-extractive")
        != "local-extractive"
    ):
        try:
            return (
                "openai",
                OpenAIRagConfidenceNormalizer(
                    getattr(settings, "llm_model_name", "gpt-4o-mini")
                ),
            )
        except Exception:
            pass
    return ("local", LocalRagConfidenceNormalizer())


def _normalize_competitors(
    analysis: AnalysisRead,
) -> tuple[float, list[dict[str, Any]]]:
    candidates = _build_normalizer_candidates(analysis)
    if not candidates:
        return 0.0, []

    capped_candidates = candidates[:200]
    norm_via, normalizer = _build_rag_normalizer(capped_candidates=capped_candidates)
    threshold = 0.6
    total = 0
    hits = 0
    normalization_details: list[dict[str, Any]] = []
    for competitor in analysis.insights.competitors or []:
        try:
            original = str(getattr(competitor, "name", "") or "").strip()
            if not original:
                continue
            total += 1
            mapped, confidence = normalizer.normalize(
                original,
                candidates=capped_candidates,
            )
            accepted = bool(
                mapped and mapped != original and confidence >= threshold
            )
            if accepted:
                competitor.name = mapped  # type: ignore[attr-defined]
                hits += 1
            normalization_details.append(
                {
                    "original": original,
                    "mapped": mapped or original,
                    "confidence": round(confidence, 3),
                    "accepted": accepted,
                    "via": norm_via,
                    "candidates": len(capped_candidates),
                }
            )
        except Exception:
            continue
    normalization_rate = (hits / total) if total > 0 else 0.0
    return normalization_rate, normalization_details


def _ensure_action_items(analysis: AnalysisRead) -> list[OpportunityReportOut]:
    if analysis.insights.action_items:
        return list(analysis.insights.action_items)
    generated = build_opportunity_reports(analysis.insights.model_dump(mode="json"))
    return [
        OpportunityReportOut.model_validate(item.to_dict())
        for item in generated
    ]


def _mark_insufficient_evidence(
    action_items: Sequence[OpportunityReportOut],
) -> list[OpportunityReportOut]:
    normalized_items: list[OpportunityReportOut] = []
    for item in action_items:
        try:
            url_count = sum(
                1 for evidence in (item.evidence_chain or []) if getattr(evidence, "url", None)
            )
            if url_count < 2:
                tips = list(item.suggested_actions or [])
                marker = "证据不足(n<2)"
                if marker not in tips:
                    tips.append(marker)
                item = _clone_action_item(item, suggested_actions=tips)
        except Exception:
            pass
        normalized_items.append(item)
    return normalized_items


async def _summarize_action_item_evidence(
    action_items: Sequence[OpportunityReportOut],
) -> list[OpportunityReportOut]:
    summarizer = None
    if (
        getattr(settings, "enable_llm_summary", True)
        and getattr(settings, "llm_model_name", "local-extractive")
        != "local-extractive"
    ):
        try:
            from app.services.llm.openai_summarizer import (
                OpenAISummarizer as _OpenAISummarizer,
            )

            summarizer = _OpenAISummarizer(
                model=getattr(settings, "llm_model_name", "gpt-4o-mini")
            )
        except Exception:
            summarizer = None
    if summarizer is None:
        summarizer = LocalExtractiveSummarizer()

    from app.services.llm.interfaces import EvidenceText

    transformed: list[OpportunityReportOut] = []
    for item in action_items:
        evidences = item.evidence_chain or []
        evidence_payload = [
            EvidenceText(
                title=str(getattr(evidence, "title", "") or ""),
                note=str(getattr(evidence, "note", "") or ""),
                url=getattr(evidence, "url", None),
            )
            for evidence in evidences
        ]
        summaries = summarizer.summarize_evidences(evidence_payload, max_chars=28)
        new_chain = []
        for evidence, summary in zip(evidences, summaries):
            try:
                new_chain.append(
                    type(evidence)(
                        title=evidence.title,
                        url=evidence.url,
                        note=summary or (evidence.note or ""),
                    )
                )
            except Exception:
                new_chain.append(evidence)
        transformed.append(_clone_action_item(item, evidence_chain=new_chain))
    return transformed


def _decorate_action_item_titles(
    *,
    action_items: list[OpportunityReportOut],
    opportunities: Sequence[Any],
) -> None:
    if not (
        getattr(settings, "enable_llm_summary", True)
        and getattr(settings, "llm_model_name", "local-extractive")
        != "local-extractive"
    ):
        return
    try:
        from app.services.llm.title_slogan import TitleSloganGenerator

        generator = TitleSloganGenerator(
            model=getattr(settings, "llm_model_name", "gpt-4o-mini")
        )
        for idx, item in enumerate(action_items):
            try:
                opportunity = opportunities[idx] if idx < len(opportunities) else None
                description = item.problem_definition or (
                    opportunity.description if opportunity else ""
                )
                title = generator.generate_title(description)
                slogan = generator.generate_slogan(description)
                suggestions = list(item.suggested_actions or [])
                if title:
                    suggestions.insert(0, f"Title: {title}")
                if slogan:
                    suggestions.insert(1 if title else 0, f"Slogan: {slogan}")
                action_items[idx] = _clone_action_item(
                    item,
                    suggested_actions=suggestions[: max(3, len(suggestions))],
                )
            except Exception:
                continue
    except Exception:
        return


def _derive_action_title(text: str) -> str:
    if not text:
        return ""
    value = text.strip()
    for separator in ("。", "，", ".", ",", "；", ";", ":", "：", "-", "—"):
        if separator in value:
            value = value.split(separator, 1)[0].strip()
            break
    return value[:18] if len(value) > 18 else value


def _finalize_action_items(action_items: list[OpportunityReportOut]) -> None:
    for item in action_items:
        if not getattr(item, "category", None):
            item.category = "strategy"
        if not getattr(item, "title", None):
            extracted = None
            for action in item.suggested_actions or []:
                if isinstance(action, str) and action.strip().startswith("Title:"):
                    extracted = action.split(":", 1)[1].strip()
                    break
            item.title = (
                extracted
                or _derive_action_title(item.problem_definition or "")
                or None
            )


def _recalibrate_opportunity_scale(analysis: AnalysisRead) -> None:
    try:
        from app.services.analysis.scoring_rules import ScoringRulesLoader

        loader = ScoringRulesLoader()
        rules = loader.load()
        estimator = getattr(rules, "opportunity_estimator", None)
        scale_weight = float(getattr(estimator, "scale_weight", 0.2) or 0.2)
        details = analysis.sources.communities_detail or []
        avg_daily = 0.0
        if details:
            values = [
                float(getattr(detail, "daily_posts", 0) or 0)
                for detail in details
                if getattr(detail, "daily_posts", None) is not None
            ]
            if values:
                avg_daily = sum(values) / max(1, len(values))
        scale = avg_daily / (avg_daily + 50.0) if avg_daily > 0 else 0.0
        multiplier = max(0.8, min(2.0, 1.0 + scale_weight * scale))
        for opportunity in analysis.insights.opportunities:
            try:
                if getattr(opportunity, "potential_users_est", None) is None:
                    continue
                value = int(getattr(opportunity, "potential_users_est"))
                new_value = max(0, int(value * multiplier))
                opportunity.potential_users_est = new_value  # type: ignore[attr-defined]
                opportunity.potential_users = f"约{new_value}个潜在团队"  # type: ignore[attr-defined]
            except Exception:
                continue
    except Exception:
        return


async def build_report_enrichment_result(
    *,
    enrichment_input: ReportEnrichmentInput,
) -> ReportEnrichmentResult:
    analysis = enrichment_input.analysis
    normalization_rate = 0.0
    normalization_details: list[dict[str, Any]] = []
    if (
        not enrichment_input.blocked_by_quality_gate
        and enrichment_input.inline_llm_enabled
    ):
        try:
            normalization_rate, normalization_details = _normalize_competitors(analysis)
        except Exception:
            normalization_rate = 0.0
            normalization_details = []

    action_items = _ensure_action_items(analysis)
    action_items = _mark_insufficient_evidence(action_items)
    if (
        not enrichment_input.blocked_by_quality_gate
        and enrichment_input.inline_llm_enabled
    ):
        try:
            action_items = await _summarize_action_item_evidence(action_items)
        except Exception:
            pass
        _decorate_action_item_titles(
            action_items=action_items,
            opportunities=analysis.insights.opportunities,
        )
    _finalize_action_items(action_items)
    _recalibrate_opportunity_scale(analysis)
    return ReportEnrichmentResult(
        action_items=action_items,
        normalization_rate=normalization_rate,
        normalization_details=normalization_details,
    )


def write_report_enrichment_audit(
    *,
    task_id: UUID,
    llm_model: str | None,
    enrichment_result: ReportEnrichmentResult,
    output_root: Path | None = None,
) -> None:
    output_dir = output_root or Path("backend/reports/local-acceptance")
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": str(task_id),
        "llm_model": llm_model,
        "normalization_rate": round(enrichment_result.normalization_rate, 3),
        "details": {"normalizations": enrichment_result.normalization_details},
    }
    output_path = output_dir / f"llm-audit-{task_id}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "ReportEnrichmentInput",
    "ReportEnrichmentResult",
    "build_report_enrichment_result",
    "write_report_enrichment_audit",
]
