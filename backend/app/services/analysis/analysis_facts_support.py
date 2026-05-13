from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional, Any, Callable, Mapping, Sequence

from app.services.analysis.signal_extraction import BusinessSignals, CompetitorSignal


@dataclass(slots=True)
class CommentSignalPreparation:
    comment_lookup: dict[str, dict[str, Any]]
    comment_signal_inputs: list[dict[str, Any]]


@dataclass(slots=True)
class FactsSignalArtifacts:
    high_value_pains: list[dict[str, Any]]
    brand_pain: list[dict[str, Any]]
    solutions_block: list[dict[str, Any]]
    aggregates: dict[str, Any]
    source_range: dict[str, int]


def prepare_comment_signal_inputs(
    sample_comments_db: Sequence[Mapping[str, Any]],
) -> CommentSignalPreparation:
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

    return CommentSignalPreparation(
        comment_lookup=comment_lookup,
        comment_signal_inputs=comment_signal_inputs,
    )


def build_facts_signal_artifacts(
    *,
    business_signals: BusinessSignals,
    comment_signals:Optional[ BusinessSignals],
    deduped_posts: Sequence[Mapping[str, Any]],
    sample_comments_db: Sequence[Mapping[str, Any]],
    comment_counts_by_subreddit: Mapping[str, int],
    post_lookup: Mapping[str, Mapping[str, Any]],
    comment_lookup: Mapping[str, Mapping[str, Any]],
    normalise_community_name: Callable[[str], str],
    cluster_pain_signals_for_facts: Callable[..., list[dict[str, Any]]],
) -> FactsSignalArtifacts:
    def unique_authors(source_ids: Sequence[str]) -> int:
        authors: set[str] = set()
        for pid in source_ids:
            payload = post_lookup.get(pid)
            author = ""
            if payload:
                author = str(payload.get("author") or "").strip()
            else:
                comment_payload = comment_lookup.get(pid) or {}
                author = str(
                    comment_payload.get("author")
                    or comment_payload.get("author_name")
                    or comment_payload.get("author_id")
                    or ""
                ).strip()
            author = author.lower()
            if author:
                authors.add(author)
        return len(authors)

    def evidence_count(source_id: str) -> int:
        payload = post_lookup.get(source_id)
        if not payload:
            return 1
        raw = payload.get("evidence_count", 1)
        try:
            count = int(raw or 1)
        except (TypeError, ValueError):
            count = 1
        return max(1, count)

    def evidence_ids(source_ids: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for pid in source_ids:
            payload = post_lookup.get(pid) or {}
            ids = payload.get("evidence_post_ids") or [pid]
            if not isinstance(ids, list):
                ids = [pid]
            for raw in ids:
                item = str(raw or "").strip()
                if not item or item in seen:
                    continue
                seen.add(item)
                out.append(item)
                if len(out) >= 50:
                    return out
        return out

    def evidence_quote_ids(source_ids: Sequence[str]) -> list[str]:
        candidates: list[tuple[int, str]] = []
        for sid in source_ids:
            payload = comment_lookup.get(sid)
            if not payload:
                continue
            try:
                score = int(payload.get("score") or 0)
            except (TypeError, ValueError):
                score = 0
            candidates.append((score, sid))
        candidates.sort(key=lambda item: item[0], reverse=True)

        seen: set[str] = set()
        out: list[str] = []
        for _score, sid in candidates:
            if sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
            if len(out) >= 5:
                return out

        for sid in evidence_ids(source_ids):
            if sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
            if len(out) >= 5:
                break
        return out

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
        build_brand_pain_entry(comp, unique_authors=unique_authors, evidence_quote_ids=evidence_quote_ids)
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

    subreddit_counts = Counter()
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

    return FactsSignalArtifacts(
        high_value_pains=high_value_pains,
        brand_pain=brand_pain,
        solutions_block=solutions_block,
        aggregates=aggregates,
        source_range={"posts": len(deduped_posts), "comments": len(sample_comments_db)},
    )


def build_brand_pain_entry(
    competitor: CompetitorSignal,
    *,
    unique_authors: Callable[[Sequence[str]], int],
    evidence_quote_ids: Callable[[Sequence[str]], list[str]],
) -> dict[str, Any]:
    return {
        "name": str(competitor.name or "").strip(),
        "mentions": int(competitor.mention_count or 0),
        "unique_authors": unique_authors(competitor.source_posts),
        "evidence_quote_ids": evidence_quote_ids(competitor.source_posts),
    }
