from __future__ import annotations

from app.services.analysis.signal_extraction import PainPointSignal
from app.services.analysis.analysis_engine import _cluster_pain_signals_for_facts


def test_cluster_pain_signals_for_facts_rolls_up_mentions_and_authors() -> None:
    pains: list[PainPointSignal] = []
    for idx in range(10):
        pains.append(
            PainPointSignal(
                description="This workflow is expensive and frustrating to use.",
                frequency=1,
                sentiment=-0.6,
                keywords=["pricing"],
                source_posts=[f"p{idx}"],
                relevance=0.5,
            )
        )
    for idx in range(2):
        pains.append(
            PainPointSignal(
                description="The dashboard feels painfully slow and confusing.",
                frequency=1,
                sentiment=-0.5,
                keywords=["performance"],
                source_posts=[f"s{idx}"],
                relevance=0.4,
            )
        )

    def evidence_count(_: str) -> int:
        return 1

    def unique_authors(source_ids: list[str]) -> int:
        return len(set(source_ids))

    def evidence_quote_ids(source_ids: list[str]) -> list[str]:
        return source_ids[:5]

    clusters = _cluster_pain_signals_for_facts(
        pains,
        evidence_count=evidence_count,
        unique_authors=unique_authors,
        evidence_quote_ids=evidence_quote_ids,
    )

    assert clusters, "Expected at least one rolled-up pain cluster"

    overall = next((c for c in clusters if c.get("title") == "主要抱怨（汇总）"), None)
    assert overall is not None
    overall_metrics = overall.get("metrics") or {}
    assert int(overall_metrics.get("mentions") or 0) == 12
    assert int(overall_metrics.get("unique_authors") or 0) == 12
    assert overall.get("evidence_quote_ids"), "Expected evidence ids for overall cluster"

    cost_cluster = next((c for c in clusters if c.get("title") == "太贵/成本高"), None)
    assert cost_cluster is not None
    cost_metrics = cost_cluster.get("metrics") or {}
    assert int(cost_metrics.get("mentions") or 0) == 10
    assert int(cost_metrics.get("unique_authors") or 0) == 10
    assert cost_cluster.get("evidence_quote_ids"), "Expected evidence ids for cost cluster"

