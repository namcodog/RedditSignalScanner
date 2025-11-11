import pytest

from backend.app.services.analysis.hybrid_matcher import HybridMatcher, Term


def test_exact_matching_word_boundary():
    terms = [
        Term(canonical="Amazon", aliases=["AMZ"], precision_tag="exact", category="brands"),
    ]
    m = HybridMatcher(terms)

    res = m.match_text("I sell on Amazon")
    assert any(r.canonical == "Amazon" and r.match_type == "exact" for r in res)

    # boundary negative case
    res2 = m.match_text("Amazonian rainforest is huge")
    assert all(r.match_type != "exact" for r in res2)


def test_alias_matching():
    terms = [
        Term(canonical="Amazon", aliases=["AMZ"], precision_tag="exact", category="brands"),
    ]
    m = HybridMatcher(terms)
    res = m.match_text("AMZ fees are high")
    assert any(r.canonical == "Amazon" for r in res)


def test_phrase_matching():
    terms = [
        Term(canonical="drop shipping", aliases=["dropshipping", "drop-shipping"], precision_tag="phrase", category="features"),
    ]
    m = HybridMatcher(terms)
    res = m.match_text("Is drop-shipping still viable? I tried dropshipping last year.")
    # at least one phrase hit
    assert any(r.canonical == "drop shipping" and r.match_type == "phrase" for r in res)


def test_aggregate_helpers():
    terms = [
        Term(canonical="Amazon", aliases=["AMZ"], precision_tag="exact", category="brands"),
        Term(canonical="drop shipping", aliases=["dropshipping"], precision_tag="phrase", category="features"),
    ]
    m = HybridMatcher(terms)
    res = m.match_text("Amazon and dropshipping, AMZ too. dropshipping!")
    by_cat = m.aggregate_by_category(res)
    assert set(by_cat.keys()) == {"brands", "features"}
    by_can = m.aggregate_by_canonical(res)
    assert "Amazon" in by_can and "drop shipping" in by_can

