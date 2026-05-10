from __future__ import annotations

from typing import Any

from app.schemas.hotpost_card_drafts import WritingCardDraft
from app.schemas.hotpost_card_review import BreakdownSuggestion


def suggestion_case(suggestion: BreakdownSuggestion, draft: WritingCardDraft) -> dict[str, Any]:
    return {
        "eval_case_id": f"breakdown-eval-suggestion-{suggestion.suggestion_id}",
        "sample_origin": "suggestion_write",
        "input_bundle": {
            "source_scope_id": suggestion.source_scope_id,
            "topic_pack_id": suggestion.topic_pack_id,
            "suggestion_id": suggestion.suggestion_id,
            "candidate_ids": suggestion.candidate_ids,
            "thread_count": suggestion.thread_count,
            "community_count": suggestion.community_count,
            "intent_tags": suggestion.intent_tags,
            "hypothesis": suggestion.hypothesis,
            "reason_codes": suggestion.reason_codes,
            "evidence_quotes": [quote.model_dump(mode="json") for quote in draft.evidence_quotes],
            "source_communities": draft.source_communities,
        },
        "baseline_output": draft_output(draft),
        "metadata": {"draft_id": draft.draft_id, "card_id": draft.card_id, "case_polarity": "pending_review"},
    }


def draft_case(draft: WritingCardDraft) -> dict[str, Any]:
    return {
        "eval_case_id": f"breakdown-eval-draft-{draft.draft_id}",
        "sample_origin": "draft_write",
        "input_bundle": {
            "source_scope_id": draft.source_scope_id,
            "topic_pack_id": None,
            "suggestion_id": None,
            "candidate_ids": draft.candidate_ids,
            "thread_count": draft.thread_count,
            "community_count": draft.community_count,
            "intent_tags": draft.intent_tags,
            "hypothesis": "",
            "reason_codes": [],
            "evidence_quotes": [quote.model_dump(mode="json") for quote in draft.evidence_quotes],
            "source_communities": draft.source_communities,
        },
        "baseline_output": draft_output(draft),
        "metadata": {"draft_id": draft.draft_id, "card_id": draft.card_id, "case_polarity": "pending_review"},
    }


def published_case(item: dict[str, Any]) -> dict[str, Any]:
    source = item["source_module"]
    quotes = item.get("quotes") or [item["preview_quote"]]
    return {
        "eval_case_id": f"breakdown-eval-published-{item['card_id']}",
        "sample_origin": "published_write",
        "input_bundle": {
            "source_scope_id": item["source_scope_id"],
            "topic_pack_id": item.get("topic_pack_id"),
            "suggestion_id": None,
            "candidate_ids": item.get("candidate_ids") or [],
            "thread_count": source["thread_count"],
            "community_count": source["community_count"],
            "intent_tags": item.get("intent_tags") or [],
            "hypothesis": item.get("detail", {}).get("thesis", ""),
            "reason_codes": [],
            "evidence_quotes": quotes,
            "source_communities": source["primary_communities"],
        },
        "baseline_output": {
            "title": item["title"],
            "summary_line": item["summary_line"],
            "audience": item["audience"],
            "why_now": item["why_now"],
            "detail": item["detail"],
        },
        "metadata": {"card_id": item["card_id"], "case_polarity": "published"},
    }


def draft_output(draft: WritingCardDraft) -> dict[str, Any]:
    return {
        "title": draft.title,
        "summary_line": draft.summary_line,
        "audience": draft.audience,
        "why_now": draft.why_now,
        "detail": draft.detail.model_dump(mode="json") if hasattr(draft.detail, "model_dump") else draft.detail,
    }


def empty_label(eval_case_id: str) -> dict[str, Any]:
    return {
        "eval_case_id": eval_case_id,
        "overall_pass": None,
        "field_passes": {"title": None, "summary_line": None, "audience": None, "why_now": None, "thesis": None, "quote_pack": None},
        "failure_tags": [],
        "review_notes": "",
        "review_status": "pending",
    }


def case_signature(item: dict[str, Any]) -> str:
    candidate_ids = item["input_bundle"]["candidate_ids"]
    return "|".join(sorted(candidate_ids)) if candidate_ids else item["eval_case_id"]


__all__ = [
    "case_signature",
    "draft_case",
    "empty_label",
    "published_case",
    "suggestion_case",
]
