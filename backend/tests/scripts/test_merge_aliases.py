from __future__ import annotations

from pathlib import Path

import pytest

from backend.scripts.merge_aliases import (
    ACCEPT_DECISIONS,
    AliasRow,
    CandidateTerm,
    LexiconTerm,
    apply_alias_rows_to_lexicon,
    compute_alias_candidates,
)


def _lexicon_stub() -> dict:
    return {
        "version": "vtest",
        "layers": {
            "L2": {
                "brands": [
                    {
                        "canonical": "Amazon",
                        "aliases": ["Amazon.com"],
                        "precision_tag": "exact",
                        "weight": 120.0,
                    }
                ],
                "features": [
                    {
                        "canonical": "ad spend",
                        "aliases": [],
                        "precision_tag": "phrase",
                        "weight": 42.0,
                    }
                ],
            },
            "L3": {
                "features": [
                    {
                        "canonical": "checkout flow",
                        "aliases": ["checkout process"],
                        "precision_tag": "phrase",
                        "weight": 87.0,
                    }
                ],
                "pain_points": [
                    {
                        "canonical": "account suspension",
                        "aliases": [],
                        "precision_tag": "phrase",
                        "weight": 65.0,
                        "polarity": "negative",
                    }
                ],
            },
        },
    }


def test_compute_alias_candidates_prefers_matching_layer_and_category() -> None:
    lex_terms = [
        LexiconTerm(canonical="Amazon", layer="L2", category="brands", aliases=["Amazon.com"]),
        LexiconTerm(canonical="checkout flow", layer="L3", category="features", aliases=["checkout process"]),
    ]

    candidates = [
        CandidateTerm(term="amz", layer="L2", category="brands", freq=120, score=9.4),
        CandidateTerm(term="check out flow", layer="L3", category="features", freq=33, score=7.1),
        CandidateTerm(term="totally different", layer="L1", category="features", freq=5, score=1.0),
    ]

    suggestions = compute_alias_candidates(
        lexicon_terms=lex_terms,
        candidate_terms=candidates,
        min_score=0.75,
        layer_aware=True,
        top_k=2,
    )

    assert any(s.alias == "amz" and s.canonical == "Amazon" for s in suggestions)
    assert any(s.alias == "check out flow" and s.canonical == "checkout flow" for s in suggestions)
    assert all(s.score >= 0.75 for s in suggestions)


def test_apply_alias_rows_to_lexicon_respects_decisions(tmp_path: Path) -> None:
    lexicon = _lexicon_stub()
    rows = [
        AliasRow(
            canonical="Amazon",
            alias="amz",
            target_layer="L2",
            target_category="brands",
            candidate_layer="L2",
            candidate_category="brands",
            jaro=0.92,
            cosine=0.66,
            context_bonus=0.05,
            score=0.88,
            freq=120,
            decision="approve",
            notes="common shorthand",
        ),
        AliasRow(
            canonical="Amazon",
            alias="amazon",
            target_layer="L2",
            target_category="brands",
            candidate_layer="L2",
            candidate_category="brands",
            jaro=1.0,
            cosine=1.0,
            context_bonus=0.05,
            score=1.0,
            freq=900,
            decision="pending",
            notes="duplicate of canonical",
        ),
    ]

    applied = apply_alias_rows_to_lexicon(lexicon, rows, ACCEPT_DECISIONS)

    entry = lexicon["layers"]["L2"]["brands"][0]
    assert applied == 1
    assert "amz" in entry.get("aliases", [])
    assert "amazon" not in entry.get("aliases", [])
