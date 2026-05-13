from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Optional, Any

from app.services.analysis.signal_extraction import BusinessSignals


@dataclass(slots=True)
class FactsSignalArtifacts:
    comment_lookup: dict[str, dict[str, Any]]
    comment_signal_inputs: list[dict[str, Any]]
    comment_signals:Optional[ BusinessSignals]
    pains_for_facts: list[Any]
    competitors_for_facts: list[Any]
    solutions_for_facts: list[Any]
    high_value_pains: list[dict[str, Any]]
    brand_pain: list[dict[str, Any]]
    solutions_block: list[dict[str, Any]]
    aggregates: dict[str, Any]
    source_range: dict[str, int]


def build_facts_signal_artifacts(
    *,
    sample_comments_db: Sequence[Mapping[str, Any]],
    business_signals: BusinessSignals,
    deduped_posts: Sequence[Mapping[str, Any]],
    comment_counts_by_subreddit: Mapping[str, int],
    keywords: Sequence[str],
    signal_extract: Callable[[Sequence[dict[str, Any]], Sequence[str]], BusinessSignals],
    normalise_community_name: Callable[[str], str],
    cluster_pain_signals_for_facts: Callable[..., list[dict[str, Any]]],
    evidence_count: Callable[[Sequence[str]], int],
    unique_authors: Callable[[Sequence[str]], int],
    evidence_quote_ids: Callable[[Sequence[str]], list[str]],
) -> FactsSignalArtifacts:
    comment_lookup = {
        str(item.get("id") or "").strip(): dict(item)
        for item in sample_comments_db
        if str(item.get("id") or "").strip()
    }
    comment_signal_inputs: list[dict[str, Any]] = []
    for cid, item in comment_lookup.items():
        body = str(item.get("text") or item.get("body") or "").strip()
        if not body:
            continue
        comment_signal_inputs.append(
            {
                "id": cid,
                "title": "",
                "summary": body,
                "score": item.get("score", 0),
                "num_comments": 0,
            }
        )

    comment_signals:Optional[ BusinessSignals] = None
    if comment_signal_inputs:
        try:
            comment_signals = signal_extract(comment_signal_inputs, keywords)
        except Exception:
            comment_signals = None

    pains_for_facts = list(business_signals.pain_points)
    competitors_for_facts = list(business_signals.competitors)
    solutions_for_facts = list(getattr(business_signals, "solutions", []) or [])
    if comment_signals is not None:
        pains_for_facts.extend(comment_signals.pain_points)
        competitors_for_facts.extend(comment_signals.competitors)
        solutions_for_facts.extend(getattr(comment_signals, "solutions", []) or [])

    high_value_pains = cluster_pain_signals_for_facts(
        pains_for_facts,
        evidence_count=evidence_count,
        unique_authors=unique_authors,
        evidence_quote_ids=evidence_quote_ids,
    )
    brand_pain = [
        {
            "name": str(comp.name or "").strip(),
            "mentions": int(comp.mention_count or 0),
            "unique_authors": unique_authors(comp.source_posts),
            "evidence_quote_ids": evidence_quote_ids(comp.source_posts),
        }
        for comp in competitors_for_facts
    ]
    solutions_block = [
        {
            "description": str(sol.description or "").strip(),
            "frequency": int(getattr(sol, "frequency", 0) or 0),
            "evidence_quote_ids": evidence_quote_ids(sol.source_posts),
        }
        for sol in solutions_for_facts
    ]
    if not solutions_block:
        solutions_block = [
            {
                "description": str(op.description or "").strip(),
                "evidence_quote_ids": evidence_quote_ids(op.source_posts),
            }
            for op in business_signals.opportunities
        ]

    subreddit_counts: Counter[str] = Counter()
    for post in deduped_posts:
        raw_name = str(post.get("subreddit") or "").strip()
        name = normalise_community_name(raw_name) if raw_name else "unknown"
        subreddit_counts[name] += 1
    aggregates = {
        "communities": [
            {
                "name": name,
                "posts": int(count),
                "comments": int(comment_counts_by_subreddit.get(name, 0)),
            }
            for name, count in subreddit_counts.most_common()
        ]
    }
    source_range = {"posts": len(deduped_posts), "comments": len(sample_comments_db)}
    return FactsSignalArtifacts(
        comment_lookup=comment_lookup,
        comment_signal_inputs=comment_signal_inputs,
        comment_signals=comment_signals,
        pains_for_facts=pains_for_facts,
        competitors_for_facts=competitors_for_facts,
        solutions_for_facts=solutions_for_facts,
        high_value_pains=high_value_pains,
        brand_pain=brand_pain,
        solutions_block=solutions_block,
        aggregates=aggregates,
        source_range=source_range,
    )


__all__ = [
    "FactsSignalArtifacts",
    "build_facts_signal_artifacts",
]
