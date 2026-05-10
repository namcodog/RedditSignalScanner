from __future__ import annotations

from typing import Optional, Any

from app.schemas.hotpost import ComplaintFacet
from app.services.hotpost.compare_evidence_entries import iter_compare_evidence_entries
from app.services.hotpost.compare_quote_signals import classify_quote_type
from app.services.hotpost.compare_targets import (
    infer_facet_target,
    resolve_compare_targets,
)
from app.services.hotpost.quote_projection import normalize_quote_text
from app.services.hotpost.rant_evidence_helpers import (
    ASCII_TERM_RE,
    CJK_TEXT_RE,
    build_focus_terms,
    build_target_terms,
    contains_term,
    extract_focus_hint,
    focus_matches_quote,
    get_payload_value,
    looks_like_complaint_quote,
)
from app.services.hotpost.rules import normalize_text
from app.services.hotpost.symptom_phrase import extract_symptom_phrase


def scope_rant_evidence_units(
    *,
    evidence_units: list[dict[str, Any]],
    query: str,
    query_family:Optional[ str],
) -> list[dict[str, Any]]:
    compare_requested = normalize_text(query_family or "") == "comparison_complaint_discovery"
    normalized_query = normalize_text(query)
    valid_units = [
        unit
        for unit in evidence_units
        if bool(unit.get("valid")) and bool(unit.get("target_hit", True))
    ]
    if not compare_requested and " vs " not in normalized_query and " 比 " not in query:
        return valid_units
    focused_units = [unit for unit in valid_units if bool(unit.get("focus_hit"))]
    return focused_units if len(focused_units) >= 2 else valid_units


def collect_rant_evidence_units(
    payload: dict[str, Any],
    *,
    complaint_facets: list[ComplaintFacet],
    query: str,
    keywords: list[str],
    query_family:Optional[ str],
) -> list[dict[str, Any]]:
    compare_requested = normalize_text(query_family or "") == "comparison_complaint_discovery"
    compare_targets = resolve_compare_targets(payload, query=query, keywords=keywords) if compare_requested else []
    focus_terms = build_focus_terms(
        query=query,
        keywords=keywords,
        focus_hint=extract_focus_hint(payload),
    )
    target_terms = build_target_terms(
        query=query,
        keywords=keywords,
        compare_requested=compare_requested,
    )
    evidence_units: list[dict[str, Any]] = []
    seen_index: dict[str, int] = {}

    def add_unit(
        *,
        quote_text: Any,
        url: Any = None,
        thread_key: Any = None,
        target: Any = None,
        quote_id: Any = None,
        subreddit: Any = None,
        created_utc: Any = None,
        score: Any = None,
        source: str = "top_quote",
        source_type: str = "quote",
        side: Any = None,
        stance: Any = None,
        side_resolution_source: Any = None,
        focus_resolution_source: Any = None,
        confidence: Any = None,
        force_valid:Optional[ bool] = None,
    ) -> None:
        quote = normalize_quote_text(quote_text, max_chars=220)
        normalized_quote = normalize_text(quote)
        if not normalized_quote:
            return
        inferred_target = str(target or "").strip() or infer_facet_target(
            text=quote,
            query=query,
            keywords=keywords,
        )
        quote_type = classify_quote_type(quote, complaint_detector=looks_like_complaint_quote)
        focus_hit = True
        if focus_terms:
            focus_hit = focus_matches_quote(
                normalized_quote=normalized_quote,
                focus_terms=focus_terms,
            )
        target_hit = True
        if target_terms and source in {"top_quote", "pain_point", "facet"}:
            target_hit = any(contains_term(normalized_quote, term) for term in target_terms)
        focus_gate_required = False
        if compare_requested and focus_terms:
            has_ascii_focus = any(ASCII_TERM_RE.search(str(term).lower()) for term in focus_terms)
            quote_has_cjk = bool(CJK_TEXT_RE.search(quote))
            focus_gate_required = has_ascii_focus or quote_has_cjk
        focus_gate_passed = focus_hit if focus_gate_required else True
        valid = force_valid if force_valid is not None else (
            quote_type in {"complaint", "compare"}
            and target_hit
            and focus_gate_passed
            and (compare_requested or looks_like_complaint_quote(quote))
        )
        candidate_unit = {
            "quote": quote,
            "url": str(url or "").strip(),
            "thread_key": str(thread_key or "").strip(),
            "thread_id": str(thread_key or "").strip() or None,
            "target": str(side or inferred_target or "").strip(),
            "quote_id": str(quote_id or "").strip(),
            "comment_id": str(quote_id or "").strip() if str(source_type or "") == "comment" else None,
            "subreddit": str(subreddit or "").strip(),
            "created_utc": created_utc,
            "score": int(score or 0),
            "quote_type": quote_type,
            "symptom_phrase": extract_symptom_phrase(quote),
            "focus_hit": focus_hit,
            "target_hit": target_hit,
            "source": source,
            "source_type": source_type,
            "side": str(side or "").strip() or None,
            "stance": str(stance or "").strip() or None,
            "side_resolution_source": str(side_resolution_source or "").strip() or None,
            "focus_resolution_source": str(focus_resolution_source or "").strip() or None,
            "confidence": float(confidence) if confidence is not None else None,
            "valid": valid,
        }
        dedupe_key = normalized_quote if not compare_requested or not candidate_unit["side"] else f"{normalized_quote}::{candidate_unit['side']}"
        existing_index = seen_index.get(dedupe_key)
        if existing_index is not None:
            existing = evidence_units[existing_index]
            if bool(existing.get("valid")) or not valid:
                return
            evidence_units[existing_index] = candidate_unit
            return
        seen_index[dedupe_key] = len(evidence_units)
        evidence_units.append(candidate_unit)

    if compare_requested:
        for entry in iter_compare_evidence_entries(
            payload=payload,
            compare_targets=compare_targets,
            focus_terms=focus_terms,
            complaint_detector=looks_like_complaint_quote,
        ):
            add_unit(**entry)
    else:
        for quote in list(payload.get("top_quotes") or []):
            quote_text = get_payload_value(quote, "quote")
            add_unit(
                quote_text=quote_text,
                url=get_payload_value(quote, "url") or get_payload_value(quote, "thread_url"),
                thread_key=(
                    get_payload_value(quote, "thread_id")
                    or get_payload_value(quote, "thread_url")
                    or get_payload_value(quote, "url")
                    or quote_text
                ),
                quote_id=get_payload_value(quote, "quote_id"),
                subreddit=get_payload_value(quote, "subreddit"),
                created_utc=get_payload_value(quote, "created_utc"),
                score=get_payload_value(quote, "score"),
                source="top_quote",
            )

    for facet in complaint_facets:
        evidence_urls = list(facet.evidence_urls or [])
        add_unit(
            quote_text=facet.representative_quote,
            url=evidence_urls[0] if evidence_urls else None,
            thread_key=evidence_urls[0] if evidence_urls else None,
            target=facet.target,
            source="facet",
        )

    for point in list(payload.get("pain_points") or []):
        evidence_urls = list(get_payload_value(point, "evidence_urls") or [])
        add_unit(
            quote_text=get_payload_value(point, "user_voice"),
            url=evidence_urls[0] if evidence_urls else None,
            thread_key=evidence_urls[0] if evidence_urls else None,
            source="pain_point",
        )
        for sample in list(get_payload_value(point, "sample_quotes") or []):
            add_unit(quote_text=sample, source="pain_point")
        for evidence in list(get_payload_value(point, "evidence") or []):
            add_unit(
                quote_text=get_payload_value(evidence, "key_quote"),
                url=get_payload_value(evidence, "url"),
                thread_key=get_payload_value(evidence, "url"),
                source="pain_point",
            )

    valid_unit_count = sum(1 for unit in evidence_units if bool(unit.get("valid")))
    if valid_unit_count < 3:
        for post in list(payload.get("top_posts") or []):
            add_unit(
                quote_text=get_payload_value(post, "title") or get_payload_value(post, "body_preview"),
                url=get_payload_value(post, "reddit_url"),
                thread_key=get_payload_value(post, "id") or get_payload_value(post, "reddit_url"),
                quote_id=f"post:{get_payload_value(post, 'id') or ''}".strip(":"),
                subreddit=get_payload_value(post, "subreddit"),
                created_utc=get_payload_value(post, "created_utc"),
                score=get_payload_value(post, "score"),
                source="post_fallback",
            )

    evidence_units.sort(
        key=lambda unit: (
            1 if bool(unit.get("valid")) else 0,
            1 if bool(unit.get("target_hit")) else 0,
            1 if bool(unit.get("focus_hit")) else 0,
            1 if str(unit.get("source_type") or "") == "comment" else 0,
            1 if str(unit.get("quote_type") or "") == "compare" else 0,
            int(unit.get("score") or 0),
            len(str(unit.get("quote") or "")),
        ),
        reverse=True,
    )
    return evidence_units
