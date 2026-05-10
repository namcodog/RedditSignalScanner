from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import re
from typing import Any, Iterable, Mapping, Optional

from app.services.hotpost.hotpost_supply_contract import get_supply_scope


_SPLIT_RE = re.compile(r"[，。！？；：,.;:|/\\\-]+")
_ASCII_RE = re.compile(r"[a-z0-9][a-z0-9_+.#-]{2,}")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP_WORDS = {
    "that",
    "this",
    "with",
    "from",
    "after",
    "before",
    "their",
    "there",
    "about",
    "into",
    "over",
    "have",
    "just",
    "then",
    "more",
    "than",
    "your",
    "when",
    "they",
    "them",
    "will",
    "would",
    "should",
    "because",
}


@dataclass(frozen=True)
class TopicTreeRecord:
    item_id: str
    lane: str
    title: str
    source_scope_id: str
    topic_pack_id: str | None
    topic_cluster_id: str | None
    topic_cluster_ids: tuple[str, ...]
    named_topic_ids: tuple[str, ...]
    community: str | None
    published_at: datetime | None
    source_event_at: datetime | None
    score_hint: float
    event_key: str
    angle_key: str
    is_new_source: bool
    is_old_source: bool


def parse_dt(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def window_records(
    records: Iterable[TopicTreeRecord],
    *,
    reference_time: datetime,
    days: int,
) -> list[TopicTreeRecord]:
    cutoff = reference_time - timedelta(days=days)
    return [record for record in records if record.published_at is not None and record.published_at >= cutoff]


def normalize_community(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    cleaned = raw.replace("r/", "").strip().lower()
    return cleaned or None


def title_terms(title: str, *, limit: int) -> tuple[str, ...]:
    ordered: list[str] = []
    for chunk in _SPLIT_RE.split(str(title or "").lower()):
        chunk = chunk.strip()
        if not chunk:
            continue
        ascii_terms = [
            term
            for term in _ASCII_RE.findall(chunk)
            if term not in _STOP_WORDS and len(term) >= 3
        ]
        if ascii_terms:
            for term in ascii_terms:
                if term not in ordered:
                    ordered.append(term)
                if len(ordered) >= limit:
                    return tuple(ordered[:limit])
            continue
        cjk_terms = _CJK_RE.findall(chunk)
        for term in cjk_terms or ([chunk[:12]] if chunk else []):
            trimmed = term.strip()
            if not trimmed or trimmed in ordered:
                continue
            ordered.append(trimmed)
            if len(ordered) >= limit:
                return tuple(ordered[:limit])
    return tuple(ordered[:limit])


def select_primary_community(item: Mapping[str, Any]) -> str | None:
    direct = normalize_community(item.get("matched_subreddit"))
    if direct:
        return direct
    top = normalize_community(item.get("top_community"))
    if top:
        return top
    for field in ("source_communities", "top_communities"):
        communities = item.get(field)
        if not isinstance(communities, list):
            continue
        for value in communities:
            normalized = normalize_community(value)
            if normalized:
                return normalized
    return None


def infer_score_hint(item: Mapping[str, Any]) -> float:
    if item.get("score_hint") is not None:
        try:
            return float(item["score_hint"])
        except (TypeError, ValueError):
            pass
    score = float(item.get("score") or 0.0)
    comments = float(item.get("num_comments") or 0.0)
    threads = float(item.get("thread_count") or 0.0)
    communities = float(item.get("community_count") or 0.0)
    return score + comments / 10.0 + threads * 8.0 + communities * 6.0


def build_topic_tree_record(
    item: Mapping[str, Any],
    *,
    reference_time: datetime,
    treat_as_published: bool,
) -> TopicTreeRecord:
    source_scope_id = str(item.get("source_scope_id") or "").strip()
    title = str(item.get("title") or "").strip()
    topic_pack_id = str(item.get("topic_pack_id") or "").strip() or None
    topic_cluster_id = str(item.get("topic_cluster_id") or "").strip() or None
    topic_cluster_ids = tuple(
        str(value).strip()
        for value in list(item.get("topic_cluster_ids") or [])
        if str(value).strip()
    )
    if topic_cluster_id and topic_cluster_id not in topic_cluster_ids:
        topic_cluster_ids = (topic_cluster_id, *topic_cluster_ids)
    named_topic_ids = tuple(str(value).strip() for value in list(item.get("named_topic_ids") or []) if str(value).strip())
    community = select_primary_community(item)
    published_at = parse_dt(item.get("published_at"))
    if published_at is None and treat_as_published:
        published_at = reference_time
    source_event_at = parse_dt(item.get("source_event_at"))
    item_id = (
        str(item.get("plan_key") or "").strip()
        or str(item.get("card_id") or "").strip()
        or str(item.get("draft_id") or "").strip()
        or str(item.get("candidate_id") or "").strip()
        or title
    )
    event_key = _event_key(item, title=title, topic_pack_id=topic_pack_id, topic_cluster_id=topic_cluster_id, named_topic_ids=named_topic_ids)
    angle_key = _angle_key(title=title, topic_pack_id=topic_pack_id)
    is_new_source = is_new_source_community(source_scope_id, topic_cluster_id, community)
    is_old_source = is_old_source_community(source_scope_id, topic_cluster_id, community)
    return TopicTreeRecord(
        item_id=item_id,
        lane=str(item.get("lane") or "").strip(),
        title=title,
        source_scope_id=source_scope_id,
        topic_pack_id=topic_pack_id,
        topic_cluster_id=topic_cluster_id,
        topic_cluster_ids=topic_cluster_ids,
        named_topic_ids=named_topic_ids,
        community=community,
        published_at=published_at,
        source_event_at=source_event_at,
        score_hint=infer_score_hint(item),
        event_key=event_key,
        angle_key=angle_key,
        is_new_source=is_new_source,
        is_old_source=is_old_source,
    )


def build_topic_tree_records(
    items: Iterable[Mapping[str, Any]],
    *,
    reference_time: datetime,
    treat_as_published: bool,
) -> list[TopicTreeRecord]:
    records: list[TopicTreeRecord] = []
    for item in items:
        scope_id = str(item.get("source_scope_id") or "").strip()
        if not scope_id:
            continue
        records.append(
            build_topic_tree_record(
                item,
                reference_time=reference_time,
                treat_as_published=treat_as_published,
            )
        )
    return records


@lru_cache(maxsize=16)
def scope_source_profile(scope_id: str) -> dict[str, dict[str, set[str]]]:
    scope = get_supply_scope(scope_id)
    clusters = dict(scope.get("topic_clusters") or {})
    profile: dict[str, dict[str, set[str]]] = {}
    for cluster_id, payload in clusters.items():
        raw = dict(payload or {})
        profile[str(cluster_id)] = {
            "primary": {normalize_community(value) for value in list(raw.get("primary_communities") or []) if normalize_community(value)},
            "candidate": {normalize_community(value) for value in list(raw.get("candidate_communities") or []) if normalize_community(value)},
        }
    return profile


def is_new_source_community(scope_id: str, cluster_id: str | None, community: str | None) -> bool:
    if not cluster_id or not community:
        return False
    cluster = scope_source_profile(scope_id).get(cluster_id) or {}
    primary = cluster.get("primary", set())
    candidate = cluster.get("candidate", set())
    return community in candidate and community not in primary


def is_old_source_community(scope_id: str, cluster_id: str | None, community: str | None) -> bool:
    if not cluster_id or not community:
        return False
    cluster = scope_source_profile(scope_id).get(cluster_id) or {}
    primary = cluster.get("primary", set())
    return community in primary


def _event_key(
    item: Mapping[str, Any],
    *,
    title: str,
    topic_pack_id: str | None,
    topic_cluster_id: str | None,
    named_topic_ids: tuple[str, ...],
) -> str:
    if named_topic_ids:
        return f"named:{named_topic_ids[0]}"
    for field in ("source_link", "thread_url", "permalink", "post_id", "signal_id"):
        raw = str(item.get(field) or "").strip()
        if raw:
            return f"{field}:{raw.lower()}"
    terms = title_terms(title, limit=2)
    base = topic_cluster_id or topic_pack_id or "unknown"
    return f"{base}:{'|'.join(terms) or title[:24].lower()}"


def _angle_key(*, title: str, topic_pack_id: str | None) -> str:
    terms = title_terms(title, limit=3)
    return f"{topic_pack_id or 'unknown'}:{'|'.join(terms) or title[:24].lower()}"


__all__ = [
    "TopicTreeRecord",
    "build_topic_tree_record",
    "build_topic_tree_records",
    "infer_score_hint",
    "is_new_source_community",
    "is_old_source_community",
    "normalize_community",
    "parse_dt",
    "scope_source_profile",
    "select_primary_community",
    "title_terms",
    "window_records",
]
