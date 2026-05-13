from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any, Mapping, Sequence

from app.services.hotpost.card_payload_store import load_drafts, load_published_cards
from app.services.hotpost.card_review_rejection_store import list_rejected_candidate_ids
from app.services.hotpost.experimental_candidate_store import load_experimental_candidates
from app.services.hotpost.hotpost_supply_contract import load_hotpost_supply_contract


SUGGEST_PROMOTE = "promote_candidate"
SUGGEST_KEEP = "keep_testing"
SUGGEST_DOWNGRADE = "downgrade"
SUGGEST_REJECT = "reject"


def load_experimental_communities() -> dict[str, list[dict[str, str]]]:
    contract = load_hotpost_supply_contract()
    rows: dict[str, list[dict[str, str]]] = {}
    for scope_id, scope in dict(contract.get("scopes") or {}).items():
        scope_rows: list[dict[str, str]] = []
        for cluster_id, cluster in dict(scope.get("topic_clusters") or {}).items():
            for community in list(cluster.get("experimental_communities") or []):
                scope_rows.append(
                    {
                        "scope_id": str(scope_id),
                        "topic_cluster_id": str(cluster_id),
                        "community": _community_key(community),
                    }
                )
        rows[str(scope_id)] = scope_rows
    return rows


def build_current_community_discovery_audit(*, report_date: date | None = None) -> dict[str, Any]:
    return build_community_discovery_audit(
        experimental_by_scope=load_experimental_communities(),
        experimental_candidates=load_experimental_candidates(),
        drafts=load_drafts(),
        published=load_published_cards(),
        rejected_candidate_ids=list_rejected_candidate_ids(),
        report_date=report_date,
    )


def build_community_discovery_audit(
    *,
    experimental_by_scope: Mapping[str, Sequence[Mapping[str, str]]],
    experimental_candidates: Sequence[Mapping[str, Any]],
    drafts: Sequence[Mapping[str, Any]],
    published: Sequence[Mapping[str, Any]],
    rejected_candidate_ids: set[str],
    report_date: date | None = None,
) -> dict[str, Any]:
    candidate_by_id = {
        str(item.get("candidate_id") or ""): item
        for item in experimental_candidates
        if str(item.get("candidate_id") or "")
    }
    draft_candidate_ids = _draft_candidate_ids(drafts)
    published_by_community = _published_by_community(published)
    rows: list[dict[str, Any]] = []

    for scope_id, communities in experimental_by_scope.items():
        for configured in communities:
            community = _community_key(configured.get("community"))
            scope = str(configured.get("scope_id") or scope_id)
            cluster_id = str(configured.get("topic_cluster_id") or "")
            community_candidates = [
                item
                for item in experimental_candidates
                if str(item.get("source_scope_id") or "") == scope
                and _community_key(item.get("matched_subreddit")) == community
            ]
            candidate_ids = {
                str(item.get("candidate_id") or "")
                for item in community_candidates
                if str(item.get("candidate_id") or "")
            }
            direct_published = [
                item
                for item in published_by_community.get(community, [])
                if str(item.get("source_scope_id") or "") == scope
            ]
            candidate_published = _published_for_candidate_ids(published, candidate_ids)
            published_evidence = _unique_published_items([*candidate_published, *direct_published])
            draft_ids = candidate_ids & draft_candidate_ids
            reject_ids = candidate_ids & rejected_candidate_ids
            post_keys = [_post_key(item) for item in community_candidates]
            duplicate_count = max(0, len(post_keys) - len({key for key in post_keys if key}))
            published_count = len(published_evidence)
            new_topic_count = len(_topic_keys(community_candidates, published_evidence))

            rows.append(
                {
                    "scope_id": scope,
                    "community": community,
                    "topic_cluster_id": cluster_id,
                    "collected_candidates": len(community_candidates),
                    "draft_count": len(draft_ids),
                    "published_count": published_count,
                    "reject_count": len(reject_ids),
                    "duplicate_count": duplicate_count,
                    "new_topic_count": new_topic_count,
                    "noise_notes": _noise_notes(
                        collected_count=len(community_candidates),
                        reject_count=len(reject_ids),
                        duplicate_count=duplicate_count,
                        published_count=published_count,
                    ),
                    "suggested_action": _suggest_action(
                        collected_count=len(community_candidates),
                        draft_count=len(draft_ids),
                        published_count=published_count,
                        reject_count=len(reject_ids),
                        duplicate_count=duplicate_count,
                    ),
                    "semantic_feedback": _semantic_feedback(
                        community_candidates,
                        published_evidence,
                        candidate_by_id=candidate_by_id,
                    ),
                }
            )

    return {
        "schema_version": "hotpost-community-discovery-audit/v1",
        "report_date": (report_date or date.today()).isoformat(),
        "contracts": {
            "experimental_communities_are_probe_only": True,
            "default_daily_collect_includes_experimental": False,
            "auto_promote": False,
            "writes_db": False,
            "experimental_candidate_store": "backend/data/hotpost/experimental_candidates/<scope>.json",
        },
        "rows": rows,
    }


def _draft_candidate_ids(drafts: Sequence[Mapping[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for item in drafts:
        ids.update(str(value) for value in list(item.get("candidate_ids") or []) if str(value))
        candidate_id = str(item.get("candidate_id") or "")
        if candidate_id:
            ids.add(candidate_id)
    return ids


def _published_for_candidate_ids(
    published: Sequence[Mapping[str, Any]], candidate_ids: set[str]
) -> list[Mapping[str, Any]]:
    if not candidate_ids:
        return []
    return [item for item in published if _item_candidate_ids(item) & candidate_ids]


def _unique_published_items(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("card_id") or "").strip()
        if not key:
            ids = sorted(_item_candidate_ids(item))
            key = ",".join(ids) or str(item.get("title") or "").strip()
        if key and key not in seen:
            seen.add(key)
            rows.append(item)
    return rows


def _item_candidate_ids(item: Mapping[str, Any]) -> set[str]:
    ids = {str(value) for value in list(item.get("candidate_ids") or []) if str(value)}
    candidate_id = str(item.get("candidate_id") or "") or _candidate_id_from_card_id(str(item.get("card_id") or ""))
    if candidate_id:
        ids.add(candidate_id)
    return ids


def _published_by_community(published: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    rows: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in published:
        for community in _item_communities(item):
            rows[community].append(item)
    return rows


def _semantic_feedback(
    candidates: Sequence[Mapping[str, Any]],
    published: Sequence[Mapping[str, Any]],
    *,
    candidate_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    items = [*candidates, *published]
    named_topic_ids = Counter(_strings_from_items(items, "named_topic_ids"))
    matched_keywords = Counter(_strings_from_items(candidates, "matched_keywords"))
    intent_tags = Counter(_strings_from_items(items, "intent_tags"))
    titles = [str(item.get("title") or "").strip() for item in items if str(item.get("title") or "").strip()]
    clusters = Counter(_strings_from_items(items, "topic_cluster_ids"))
    for item in items:
        cluster_id = str(item.get("topic_cluster_id") or "")
        if cluster_id:
            clusters[cluster_id] += 1
        for candidate_id in list(item.get("candidate_ids") or []):
            candidate = candidate_by_id.get(str(candidate_id))
            if candidate is not None:
                clusters.update(_strings_from_items([candidate], "topic_cluster_ids"))

    return {
        "frequent_entities": _top_counter_values(named_topic_ids + matched_keywords, limit=8),
        "pain_solution_tags": _top_counter_values(intent_tags + matched_keywords, limit=8),
        "sample_titles": titles[:5],
        "product_tags": _product_tags(clusters),
    }


def _topic_keys(candidates: Sequence[Mapping[str, Any]], published: Sequence[Mapping[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for item in [*candidates, *published]:
        pack = str(item.get("topic_pack_id") or "")
        cluster = str(item.get("topic_cluster_id") or "")
        for cluster_id in list(item.get("topic_cluster_ids") or []):
            keys.add(f"{pack}:{cluster_id}")
        if pack or cluster:
            keys.add(f"{pack}:{cluster}")
    return {key for key in keys if key != ":"}


def _noise_notes(*, collected_count: int, reject_count: int, duplicate_count: int, published_count: int) -> str:
    if collected_count == 0 and published_count == 0:
        return "no_signal_yet"
    notes: list[str] = []
    if reject_count:
        notes.append("review_rejections")
    if duplicate_count:
        notes.append("duplicate_posts")
    if collected_count and published_count == 0:
        notes.append("not_published_yet")
    return ", ".join(notes) if notes else ""


def _suggest_action(
    *,
    collected_count: int,
    draft_count: int,
    published_count: int,
    reject_count: int,
    duplicate_count: int,
) -> str:
    if published_count >= 2:
        return SUGGEST_PROMOTE
    if reject_count and reject_count >= max(collected_count, 1):
        return SUGGEST_REJECT
    if collected_count == 0 and draft_count == 0 and published_count == 0:
        return SUGGEST_KEEP
    if duplicate_count >= max(2, collected_count // 2):
        return SUGGEST_DOWNGRADE
    return SUGGEST_KEEP


def _candidate_id_from_card_id(card_id: str) -> str:
    if not card_id.startswith("card-cand-"):
        return ""
    for suffix in ("-validate", "-write"):
        if card_id.endswith(suffix):
            return card_id[len("card-") : -len(suffix)]
    return ""


def _post_key(item: Mapping[str, Any]) -> str:
    for key in ("post_id", "source_link"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return str(item.get("title") or "").strip().lower()


def _item_communities(item: Mapping[str, Any]) -> set[str]:
    values: list[Any] = [item.get("matched_subreddit"), item.get("top_community")]
    source_module = item.get("source_module")
    if isinstance(source_module, dict):
        values.append(source_module.get("top_community"))
        values.extend(list(source_module.get("primary_communities") or []))
    preview = item.get("preview_quote")
    if isinstance(preview, dict):
        values.append(preview.get("community"))
    for quote in list(item.get("quotes") or []):
        if isinstance(quote, dict):
            values.append(quote.get("community"))
    return {_community_key(value) for value in values if _community_key(value)}


def _strings_from_items(items: Sequence[Mapping[str, Any]], field_name: str) -> list[str]:
    values: list[str] = []
    for item in items:
        raw = item.get(field_name)
        if isinstance(raw, list):
            values.extend(str(value).strip() for value in raw if str(value).strip())
        elif str(raw or "").strip():
            values.append(str(raw).strip())
    return values


def _top_counter_values(counter: Counter[str], *, limit: int) -> list[str]:
    return [value for value, _count in counter.most_common(limit)]


def _product_tags(clusters: Counter[str]) -> list[str]:
    mapping = {
        "pet": "宠物用品选品",
        "edc": "EDC 选品",
        "outdoor": "户外用品选品",
        "desk-setup": "桌面办公选品",
        "parenting-travel": "亲子出行选品",
        "small-goods": "小件实用品选品",
        "brand-launch-and-crowdfunding": "众筹产品验证",
        "workflow-friction": "AI 工作流",
        "seo-geo": "GEO / AI 搜索",
        "funnel": "转化链路",
    }
    return [mapping[key] for key, _count in clusters.most_common() if key in mapping]


def _community_key(value: Any) -> str:
    raw = str(value or "").strip()
    if raw.startswith("r/"):
        raw = raw[2:]
    return raw.lower()


__all__ = [
    "build_community_discovery_audit",
    "build_current_community_discovery_audit",
    "load_experimental_communities",
]
