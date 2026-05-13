from __future__ import annotations

from app.services.brand_intelligence.brand_match_guard import (
    BrandMatchGuard,
    is_brand_text_match_safe,
)


def test_guard_blocks_ambiguous_accepted_phrase_without_brand_context() -> None:
    guard = BrandMatchGuard(
        guarded_statuses=frozenset({"accepted"}),
        blocked_terms=frozenset({"can do"}),
        ambiguous_terms=frozenset({"can do"}),
        context_terms=frozenset({"brand"}),
    )

    assert (
        is_brand_text_match_safe(
            "Can Do",
            "accepted",
            "I can do this with my existing tools.",
            guard,
        )
        is False
    )


def test_guard_blocks_explicit_blocked_phrase_even_with_context() -> None:
    guard = BrandMatchGuard(
        guarded_statuses=frozenset({"accepted"}),
        blocked_terms=frozenset({"can do"}),
        ambiguous_terms=frozenset({"can do"}),
        context_terms=frozenset({"brand"}),
    )

    assert (
        is_brand_text_match_safe(
            "Can Do",
            "accepted",
            "The Can Do brand showed up in reviews.",
            guard,
        )
        is False
    )


def test_guard_allows_ambiguous_phrase_with_brand_context() -> None:
    guard = BrandMatchGuard(
        guarded_statuses=frozenset({"accepted"}),
        blocked_terms=frozenset(),
        ambiguous_terms=frozenset({"sharp"}),
        context_terms=frozenset({"brand"}),
    )

    assert (
        is_brand_text_match_safe(
            "Sharp",
            "accepted",
            "The Sharp brand showed up in reviews.",
            guard,
        )
        is True
    )


def test_guard_does_not_block_verified_brands() -> None:
    guard = BrandMatchGuard(
        guarded_statuses=frozenset({"accepted"}),
        blocked_terms=frozenset(),
        ambiguous_terms=frozenset({"google"}),
        context_terms=frozenset(),
    )

    assert is_brand_text_match_safe("Google", "verified", "google ads tips", guard)
