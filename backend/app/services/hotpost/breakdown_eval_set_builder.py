from __future__ import annotations

from collections import Counter
from typing import Optional, Any, Awaitable, Callable

from app.schemas.hotpost_card_drafts import WritingCardDraft
from app.services.hotpost.breakdown_candidate_clusterer import list_breakdown_suggestions
from app.services.hotpost.breakdown_eval_case_builders import (
    case_signature,
    draft_case,
    empty_label,
    published_case,
    suggestion_case,
)
from app.services.hotpost.card_candidate_store import get_candidates
from app.services.hotpost.card_content_generator import generate_card_content
from app.services.hotpost.card_draft_store import list_drafts
from app.services.hotpost.card_group_draft_builder import seed_group_writing_draft
from app.services.hotpost.card_payload_store import load_published_cards


WritingGenerator = Callable[[WritingCardDraft], Awaitable[WritingCardDraft]]
ProgressReporter = Callable[[str], None]
BREAKDOWN_FAILURE_TAGS = [
    "weak_thesis",
    "quote_pack_not_supporting_claim",
    "no_judgment_gain",
    "reddit_restatement",
    "why_now_not_actionable",
    "audience_not_who_is_talking",
    "stitched_not_coherent",
    "reporty_title",
]
_TARGET_PACKS = ("selection-signals", "agent-builder")
_ORIGIN_PRIORITY = {"suggestion_write": 0, "draft_write": 1, "published_write": 2}


async def build_breakdown_eval_artifacts(
    *,
    target_real: int = 18,
    target_synthetic: int = 6,
    generator: WritingGenerator = generate_card_content,
    report_progress:Optional[ ProgressReporter] = None,
) -> dict[str, Any]:
    published = [published_case(item) for item in load_published_cards() if item.get("card_type") == "write"]
    drafts = [item for item in list_drafts(card_type="write") if isinstance(item, WritingCardDraft)]
    draft_by_group = {tuple(sorted(item.candidate_ids)): item for item in drafts if item.candidate_ids}
    generation_failures: list[dict[str, str]] = []
    real_cases: list[dict[str, Any]] = []
    suggestions = [item for item in list_breakdown_suggestions(limit=50) if item.topic_pack_id in _TARGET_PACKS]
    _report(report_progress, f"loaded {len(published)} published writes, {len(drafts)} write drafts, {len(suggestions)} target suggestions")
    for suggestion in suggestions:
        group_key = tuple(sorted(suggestion.candidate_ids))
        try:
            draft = draft_by_group.get(group_key)
            if draft is None:
                draft = await generator(seed_group_writing_draft(get_candidates(suggestion.candidate_ids)))
            real_cases.append(suggestion_case(suggestion, draft))
        except Exception as exc:
            generation_failures.append({"suggestion_id": suggestion.suggestion_id, "error": str(exc)})
            _report(report_progress, f"skipped {suggestion.suggestion_id}: {exc}")
    real_cases.extend(draft_case(item) for item in drafts if not item.candidate_ids or tuple(sorted(item.candidate_ids)) not in {tuple(sorted(s.candidate_ids)) for s in suggestions})
    real_cases.extend(published)
    selected = _select_real_cases(real_cases, target_real)
    labels = [empty_label(item["eval_case_id"]) for item in selected]
    synthetic_plan = _synthetic_plan(selected, target_synthetic)
    manifest = {
        "target_real": target_real,
        "target_synthetic": target_synthetic,
        "real_count": len(selected),
        "synthetic_plan_count": len(synthetic_plan),
        "generation_failure_count": len(generation_failures),
        "topic_pack_counts": dict(Counter((item["input_bundle"]["topic_pack_id"] or "unknown") for item in selected)),
        "origin_counts": dict(Counter(item["sample_origin"] for item in selected)),
    }
    return {
        "real_cases": selected,
        "labels": labels,
        "synthetic_plan": synthetic_plan,
        "generation_failures": generation_failures,
        "manifest": manifest,
    }


def _select_real_cases(cases: list[dict[str, Any]], needed: int) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    pack_counts: Counter[str] = Counter()
    for item in sorted(cases, key=_case_sort_key):
        if len(picked) >= needed:
            break
        signature = case_signature(item)
        if signature in seen:
            continue
        pack = item["input_bundle"]["topic_pack_id"] or "unknown"
        picked.append(item)
        seen.add(signature)
        pack_counts[pack] += 1
    return picked


def _case_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    pack = item["input_bundle"]["topic_pack_id"] or "unknown"
    target_rank = 0 if pack in _TARGET_PACKS else 1
    origin_rank = _ORIGIN_PRIORITY[item["sample_origin"]]
    evidence_rank = -(item["input_bundle"]["community_count"] * 10 + item["input_bundle"]["thread_count"])
    return (target_rank, origin_rank, evidence_rank, item["eval_case_id"])


def _synthetic_plan(real_cases: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    pack_counts = Counter(item["input_bundle"]["topic_pack_id"] or "unknown" for item in real_cases)
    weakest = sorted(((pack_counts.get(pack, 0), pack) for pack in _TARGET_PACKS), key=lambda item: (item[0], item[1]))
    plans: list[dict[str, Any]] = []
    for index in range(target):
        pack = weakest[index % len(weakest)][1]
        plans.append({"synthetic_case_id": f"breakdown-synth-plan-{index + 1:02d}", "topic_pack_id": pack, "target_failure_tag": BREAKDOWN_FAILURE_TAGS[index % len(BREAKDOWN_FAILURE_TAGS)], "status": "planned"})
    return plans


def _report(callback:Optional[ ProgressReporter], message: str) -> None:
    if callback is not None:
        callback(message)


__all__ = ["BREAKDOWN_FAILURE_TAGS", "build_breakdown_eval_artifacts"]
