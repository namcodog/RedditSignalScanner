from __future__ import annotations

from app.services.analysis.evidence_ledger import build_evidence_ledger, lookup_evidence_chain


def test_build_evidence_ledger_prefers_pain_examples_and_links_opportunity() -> None:
    ledger = build_evidence_ledger(
        insights={
            "pain_points": [
                {
                    "description": "回款延迟与冻结",
                    "example_posts": [
                        {
                            "title": "Stripe payout still pending after 5 days",
                            "community": "r/stripe",
                            "permalink": "/r/stripe/comments/demo/payout-delay/",
                        }
                    ],
                    "user_examples": ["钱卡在路上，补货节奏全乱了"],
                }
            ],
            "opportunities": [
                {
                    "description": "国际收款账户开通助手",
                    "linked_pain_cluster": "回款延迟与冻结",
                    "source_examples": [],
                }
            ],
        },
        sample_posts_db=[],
        sample_comments_db=[],
    )

    pain_chain = lookup_evidence_chain(
        ledger,
        section="pain_points",
        anchor="回款延迟与冻结",
    )
    assert pain_chain == [
        {
            "title": "Stripe payout still pending after 5 days",
            "url": "https://www.reddit.com/r/stripe/comments/demo/payout-delay/",
            "note": "r/stripe",
        }
    ]

    opportunity_chain = lookup_evidence_chain(
        ledger,
        section="opportunities",
        anchor="国际收款账户开通助手",
        linked_pain="回款延迟与冻结",
    )
    assert opportunity_chain == pain_chain
