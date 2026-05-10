from __future__ import annotations

from app.services.analysis.analysis_facts_support import (
    build_facts_signal_artifacts,
    prepare_comment_signal_inputs,
)
from app.services.analysis.signal_extraction import (
    BusinessSignals,
    CompetitorSignal,
    OpportunitySignal,
    PainPointSignal,
    SolutionSignal,
)


def test_prepare_comment_signal_inputs_filters_blank_comments() -> None:
    preparation = prepare_comment_signal_inputs(
        [
            {"id": "c1", "text": "payout still pending", "score": 9},
            {"id": "c2", "body": "   ", "score": 1},
            {"id": "", "text": "missing id should be skipped"},
        ]
    )

    assert list(preparation.comment_lookup) == ["c1", "c2"]
    assert preparation.comment_signal_inputs == [
        {
            "id": "c1",
            "title": "",
            "summary": "payout still pending",
            "score": 9,
            "num_comments": 0,
        }
    ]


def test_build_facts_signal_artifacts_prefers_comment_evidence_and_falls_back_to_opportunities() -> None:
    business_signals = BusinessSignals(
        pain_points=[
            PainPointSignal(
                description="payout delayed after shipping",
                frequency=5,
                sentiment=-0.8,
                keywords=["delay"],
                source_posts=["p1", "c9"],
                relevance=0.81,
            )
        ],
        competitors=[
            CompetitorSignal(
                name="PayPal",
                mention_count=4,
                sentiment=-0.4,
                context_snippets=[],
                source_posts=["p1", "c9"],
                relevance=0.77,
            )
        ],
        opportunities=[
            OpportunitySignal(
                description="international payment account helper",
                demand_score=0.72,
                unmet_need="manual onboarding",
                potential_users=800,
                source_posts=["p1", "c9"],
                relevance=0.71,
                keywords=["onboarding"],
            )
        ],
        solutions=[],
    )
    comment_signals = BusinessSignals(
        pain_points=[],
        competitors=[],
        opportunities=[],
        solutions=[
            SolutionSignal(
                description="manual payout tracker",
                frequency=2,
                sentiment=0.1,
                source_posts=["c9"],
                relevance=0.45,
            )
        ],
    )

    cluster_calls: dict[str, object] = {}

    def fake_cluster(
        pain_points: list[PainPointSignal],
        *,
        evidence_count,
        unique_authors,
        evidence_quote_ids,
    ) -> list[dict[str, object]]:
        cluster_calls["pain_count"] = len(pain_points)
        cluster_calls["quote_ids"] = evidence_quote_ids(["p1", "c9"])
        cluster_calls["authors"] = unique_authors(["p1", "c9"])
        cluster_calls["evidence_count"] = evidence_count("p1")
        return [
            {
                "topic": "回款延迟与冻结",
                "mentions": 5,
                "unique_authors": unique_authors(["p1", "c9"]),
                "evidence_quote_ids": evidence_quote_ids(["p1", "c9"]),
            }
        ]

    artifacts = build_facts_signal_artifacts(
        business_signals=business_signals,
        comment_signals=comment_signals,
        deduped_posts=[{"id": "p1", "subreddit": "PayPal"}],
        sample_comments_db=[
            {"id": "c9", "subreddit": "r/PayPal", "author": "sellerA", "score": 11}
        ],
        comment_counts_by_subreddit={"r/paypal": 3},
        post_lookup={
            "p1": {
                "author": "sellerB",
                "evidence_count": 4,
                "evidence_post_ids": ["p1", "p1b"],
            }
        },
        comment_lookup={"c9": {"author": "sellerA", "score": 11}},
        normalise_community_name=lambda raw: f"r/{raw.strip().lower()}",
        cluster_pain_signals_for_facts=fake_cluster,
    )

    assert cluster_calls == {
        "pain_count": 1,
        "quote_ids": ["c9", "p1", "p1b"],
        "authors": 2,
        "evidence_count": 4,
    }
    assert artifacts.high_value_pains[0]["evidence_quote_ids"] == ["c9", "p1", "p1b"]
    assert artifacts.brand_pain[0]["evidence_quote_ids"] == ["c9", "p1", "p1b"]
    assert artifacts.solutions_block[0]["description"] == "manual payout tracker"
    assert artifacts.aggregates["communities"] == [
        {"name": "r/paypal", "posts": 1, "comments": 3}
    ]
    assert artifacts.source_range == {"posts": 1, "comments": 1}


def test_build_facts_signal_artifacts_falls_back_to_opportunity_evidence_when_solutions_missing() -> None:
    business_signals = BusinessSignals(
        pain_points=[],
        competitors=[],
        opportunities=[
            OpportunitySignal(
                description="account onboarding helper",
                demand_score=0.65,
                unmet_need="bank setup",
                potential_users=500,
                source_posts=["p7"],
                relevance=0.6,
                keywords=["开户"],
            )
        ],
        solutions=[],
    )

    artifacts = build_facts_signal_artifacts(
        business_signals=business_signals,
        comment_signals=None,
        deduped_posts=[],
        sample_comments_db=[],
        comment_counts_by_subreddit={},
        post_lookup={"p7": {"evidence_post_ids": ["p7", "p8"]}},
        comment_lookup={},
        normalise_community_name=lambda raw: raw,
        cluster_pain_signals_for_facts=lambda *args, **kwargs: [],
    )

    assert artifacts.solutions_block == [
        {
            "description": "account onboarding helper",
            "evidence_quote_ids": ["p7", "p8"],
        }
    ]
