from __future__ import annotations

from collections import Counter
from typing import Optional, Any, Awaitable, Callable

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.services.hotpost.card_content_generator import generate_card_content
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.card_payload_store import load_candidates, load_published_cards


SignalGenerator = Callable[[ValidationCardDraft], Awaitable[ValidationCardDraft]]
ProgressReporter = Callable[[str], None]
SIGNAL_FAILURE_TAGS = [
    "reddit_restatement",
    "no_judgment_gain",
    "audience_not_who_is_talking",
    "why_now_not_actionable",
    "reporty_title",
    "evidence_overclaim",
    "generic_copy",
    "quote_not_used_well",
]


async def build_signal_eval_artifacts(
    *,
    target_real: int = 36,
    target_synthetic: int = 12,
    generator: SignalGenerator = generate_card_content,
    report_progress:Optional[ ProgressReporter] = None,
) -> dict[str, Any]:
    real_cases = [_published_case(item) for item in load_published_cards() if item.get("card_type") == "validate"]
    candidates = [CandidatePack.model_validate(item) for item in load_candidates()]
    generation_failures: list[dict[str, str]] = []
    _report(report_progress, f"loaded {len(real_cases)} published validate cases and {len(candidates)} candidates")
    needed = max(target_real - len(real_cases), 0)
    selected = _select_candidates(candidates, len(candidates))
    for index, candidate in enumerate(selected, start=1):
        if len(real_cases) >= target_real:
            break
        _report(report_progress, f"generating candidate case {index}/{len(selected)}: {candidate.candidate_id}")
        try:
            draft = await generator(seed_validation_draft(candidate))
            real_cases.append(_draft_case(candidate, draft))
        except Exception as exc:
            generation_failures.append({"candidate_id": candidate.candidate_id, "error": str(exc)})
            _report(report_progress, f"skipped {candidate.candidate_id}: {exc}")
    real_cases = real_cases[:target_real]
    labels = [_empty_label(item["eval_case_id"]) for item in real_cases]
    synthetic_plan = _synthetic_plan(real_cases, target_synthetic)
    manifest = {
        "target_real": target_real,
        "target_synthetic": target_synthetic,
        "real_count": len(real_cases),
        "synthetic_plan_count": len(synthetic_plan),
        "generation_failure_count": len(generation_failures),
        "source_scope_counts": dict(Counter(item["input_bundle"]["source_scope_id"] for item in real_cases)),
        "origin_counts": dict(Counter(item["sample_origin"] for item in real_cases)),
    }
    return {
        "real_cases": real_cases,
        "labels": labels,
        "synthetic_plan": synthetic_plan,
        "generation_failures": generation_failures,
        "manifest": manifest,
    }


def _published_case(item: dict[str, Any]) -> dict[str, Any]:
    source = item["source_module"]
    return {
        "eval_case_id": f"signal-eval-published-{item['card_id']}",
        "sample_origin": "published_validate",
        "input_bundle": {
            "source_scope_id": item["source_scope_id"],
            "source_scope_name": item["source_scope_name"],
            "topic_pack_id": item.get("topic_pack_id"),
            "signal_level": item.get("signal_level"),
            "why_now_reason": item.get("why_now_reason"),
            "intent_tags": item.get("intent_tags") or [],
            "thread_count": source["thread_count"],
            "community_count": source["community_count"],
            "quote_count": len(item.get("quotes") or []),
            "source_communities": source["primary_communities"],
            "evidence_quotes": item.get("quotes") or [item["preview_quote"]],
        },
        "baseline_output": {
            "title": item["title"],
            "summary_line": item["summary_line"],
            "audience": item["audience"],
            "why_now": item["why_now"],
            "detail": item["detail"],
        },
        "metadata": {
            "card_id": item["card_id"],
            "case_polarity": "published",
        },
    }


def _draft_case(candidate: CandidatePack, draft: ValidationCardDraft) -> dict[str, Any]:
    return {
        "eval_case_id": f"signal-eval-generated-{draft.card_id}",
        "sample_origin": "candidate_generated",
        "input_bundle": {
            "source_scope_id": draft.source_scope_id,
            "source_scope_name": draft.source_scope_name,
            "topic_pack_id": candidate.topic_pack_id,
            "signal_level": draft.signal_level,
            "why_now_reason": draft.why_now_reason,
            "intent_tags": draft.intent_tags,
            "thread_count": draft.thread_count,
            "community_count": draft.community_count,
            "quote_count": len(draft.evidence_quotes),
            "source_communities": draft.source_communities,
            "evidence_quotes": [quote.model_dump(mode="json") for quote in draft.evidence_quotes],
        },
        "baseline_output": {
            "title": draft.title,
            "summary_line": draft.summary_line,
            "audience": draft.audience,
            "why_now": draft.why_now,
            "detail": _dump_json_like(draft.detail),
        },
        "metadata": {
            "candidate_id": candidate.candidate_id,
            "case_polarity": "pending_review",
        },
    }


def _select_candidates(candidates: list[CandidatePack], needed: int) -> list[CandidatePack]:
    picked: list[CandidatePack] = []
    scope_counts: Counter[str] = Counter()
    pack_counts: Counter[str] = Counter()
    seen_ids: set[str] = set()
    pool = sorted(candidates, key=lambda item: (item.signal_level, item.score, item.num_comments), reverse=True)
    for candidate in pool:
        if len(picked) >= needed:
            break
        if candidate.candidate_id in seen_ids:
            continue
        pack = candidate.topic_pack_id or "unknown"
        rank = (scope_counts[candidate.source_scope_id], pack_counts[pack], -candidate.quote_count, -candidate.score)
        picked.append((rank, candidate))
        seen_ids.add(candidate.candidate_id)
        scope_counts[candidate.source_scope_id] += 1
        pack_counts[pack] += 1
    picked.sort(key=lambda item: item[0])
    return [candidate for _, candidate in picked[:needed]]


def _synthetic_plan(real_cases: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    scope_pack_counts = Counter((item["input_bundle"]["source_scope_id"], item["input_bundle"]["topic_pack_id"] or "unknown") for item in real_cases)
    weakest = sorted(scope_pack_counts.items(), key=lambda item: (item[1], item[0][0], item[0][1]))
    plans: list[dict[str, Any]] = []
    for index in range(target):
        scope_id, pack_id = weakest[index % len(weakest)][0]
        plans.append(
            {
                "synthetic_case_id": f"signal-synth-plan-{index + 1:02d}",
                "source_scope_id": scope_id,
                "topic_pack_id": pack_id,
                "target_failure_tag": SIGNAL_FAILURE_TAGS[index % len(SIGNAL_FAILURE_TAGS)],
                "intent_heat": ["high", "medium", "low"][index % 3],
                "evidence_strength": ["weak", "medium", "strong"][index % 3],
                "status": "planned",
            }
        )
    return plans


def _empty_label(eval_case_id: str) -> dict[str, Any]:
    return {
        "eval_case_id": eval_case_id,
        "overall_pass": None,
        "field_passes": {"title": None, "summary_line": None, "audience": None, "why_now": None},
        "failure_tags": [],
        "review_notes": "",
        "review_status": "pending",
    }


def _dump_json_like(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _report(callback:Optional[ ProgressReporter], message: str) -> None:
    if callback is not None:
        callback(message)


__all__ = ["SIGNAL_FAILURE_TAGS", "build_signal_eval_artifacts"]
