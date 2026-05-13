from __future__ import annotations

from typing import Optional, Any

from app.schemas.hotpost import ComplaintFacet
from app.services.hotpost.compare_targets import infer_facet_target
from app.services.hotpost.quote_projection import normalize_quote_text
from app.services.hotpost.rant_evidence_cards import (
    collect_rant_evidence_units,
    scope_rant_evidence_units,
)
from app.services.hotpost.rules import normalize_text


GENERIC_COMPLAINT_LABELS = {
    "难用",
    "体验差",
    "流程复杂",
    "性能问题",
    "价格不值",
    "教程不清",
    "quality issue",
    "bad experience",
    "poor usability",
    "performance issue",
}
GENERIC_COMPLAINT_LABELS_NORMALIZED = {normalize_text(item) for item in GENERIC_COMPLAINT_LABELS}


def build_rant_complaint_facets(
    payload: dict[str, Any],
    *,
    query: str,
    keywords: list[str],
    query_family:Optional[ str],
) -> list[ComplaintFacet]:
    evidence_units = scope_rant_evidence_units(
        evidence_units=collect_rant_evidence_units(
            payload,
            complaint_facets=[],
            query=query,
            keywords=keywords,
            query_family=query_family,
        ),
        query=query,
        query_family=query_family,
    )
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for unit in evidence_units:
        quote_text = normalize_quote_text(unit.get("quote"), max_chars=180)
        if not quote_text:
            continue
        # facet 必须从最小抱怨短语长出来，不能再拿整句前半截冒充结论。
        label = str(unit.get("symptom_phrase") or "").strip() or quote_text[:32]
        if normalize_text(label) in GENERIC_COMPLAINT_LABELS_NORMALIZED:
            label = quote_text[:32]
        target = str(unit.get("target") or "").strip() or infer_facet_target(
            text=quote_text,
            query=query,
            keywords=keywords,
        )
        facet_key = (normalize_text(label), normalize_text(target))
        bucket = grouped.setdefault(
            facet_key,
            {
                "label": label,
                "target": target or None,
                "quote": quote_text,
                "count": 0,
                "urls": [],
            },
        )
        bucket["count"] = int(bucket.get("count") or 0) + 1
        url = str(unit.get("url") or "").strip()
        if url and url not in bucket["urls"]:
            bucket["urls"].append(url)

    facets = [
        ComplaintFacet(
            label=str(bucket["label"]),
            target=str(bucket.get("target") or "") or None,
            representative_quote=str(bucket["quote"]),
            evidence_count=int(bucket["count"]),
            evidence_urls=list(bucket["urls"])[:3],
        )
        for bucket in grouped.values()
    ]
    facets.sort(key=lambda item: (int(item.evidence_count or 0), len(str(item.label or ""))), reverse=True)
    return facets[:4]
