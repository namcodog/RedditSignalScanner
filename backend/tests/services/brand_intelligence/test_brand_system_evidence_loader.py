from __future__ import annotations

from app.services.brand_intelligence.brand_match_guard import BrandMatchGuard
from app.services.brand_intelligence.brand_system_evidence_loader import (
    BrandMentionRecord,
    build_brand_evidence_rows_from_records,
)


def test_loader_filters_only_unsafe_accepted_mentions() -> None:
    guard = BrandMatchGuard(
        guarded_statuses=frozenset({"accepted"}),
        blocked_terms=frozenset({"can do"}),
        ambiguous_terms=frozenset({"can do"}),
        context_terms=frozenset({"brand"}),
    )

    rows = build_brand_evidence_rows_from_records(
        (
            _record("google", "Google", "verified", "Google Ads is active."),
            _record("can-do", "Can Do", "accepted", "I can do this today."),
            _record("dyson", "Dyson", "accepted", "Dyson reviews are strong."),
        ),
        guard=guard,
        min_mentions=1,
        limit=10,
    )

    assert [row.display_name for row in rows] == ["Dyson", "Google"]


def _record(
    brand_key: str,
    name: str,
    status: str,
    source_text: str,
) -> BrandMentionRecord:
    return BrandMentionRecord(
        brand_key=brand_key,
        display_name=name,
        evidence_status=status,
        business_domains=("AI 工具",),
        interest_tags=("AI工具与Agent",),
        source_text=source_text,
        community="r/test",
        latest_observed_at="2026-05-13T00:00:00",
    )
