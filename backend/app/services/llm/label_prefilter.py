from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

_SPACE_RE = re.compile(r"\s+")
_R_PREFIX_RE = re.compile(r"^r/", flags=re.IGNORECASE)

DOMAIN_ORDER: tuple[str, ...] = (
    "Home_Lifestyle",
    "Family_Parenting",
    "Tools_EDC",
    "Food_Coffee_Lifestyle",
    "Minimal_Outdoor",
    "Frugal_Living",
    "AI_Workflow",
    "Ecommerce_Business",
)

_POOL_PRIORITY = {"core": 2, "lab": 1}


def normalize_comment_body(body: str) -> str:
    return _SPACE_RE.sub(" ", body.strip()).lower()


def normalize_subreddit_key(subreddit: str) -> str:
    return _R_PREFIX_RE.sub("", subreddit.strip().lower())


def build_comment_body_hash(body: str) -> str:
    normalized = normalize_comment_body(body)
    return hashlib.md5(normalized.encode("utf-8", errors="ignore")).hexdigest()  # noqa: S324


def coerce_categories(raw: object) -> tuple[str, ...]:
    if isinstance(raw, str):
        value = raw.strip()
        return (value,) if value else ()
    if isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray)):
        values: list[str] = []
        for item in raw:
            value = str(item).strip()
            if value:
                values.append(value)
        return tuple(values)
    return ()


@dataclass(slots=True)
class CommentPrefilterStats:
    admitted: int = 0
    filtered_short: int = 0
    deduped: int = 0
    skipped_pool: int = 0
    skipped_age: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "admitted": self.admitted,
            "filtered_short": self.filtered_short,
            "deduped": self.deduped,
            "skipped_pool": self.skipped_pool,
            "skipped_age": self.skipped_age,
        }


def prefilter_comment_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    min_chars: int,
    allowed_pools: set[str] | None = None,
    min_created_utc: datetime | None = None,
) -> tuple[list[dict[str, Any]], CommentPrefilterStats]:
    stats = CommentPrefilterStats()
    seen_hashes: set[str] = set()
    admitted: list[dict[str, Any]] = []

    for row in rows:
        pool = str(row.get("business_pool") or "unscored").strip().lower()
        if allowed_pools is not None and pool not in allowed_pools:
            stats.skipped_pool += 1
            continue

        created_utc = row.get("created_utc")
        if min_created_utc is not None and isinstance(created_utc, datetime):
            if created_utc < min_created_utc:
                stats.skipped_age += 1
                continue

        body = str(row.get("body") or "").strip()
        normalized_body = normalize_comment_body(body)
        if len(normalized_body) < min_chars:
            stats.filtered_short += 1
            continue

        body_hash = build_comment_body_hash(body)
        if body_hash in seen_hashes:
            stats.deduped += 1
            continue
        seen_hashes.add(body_hash)

        item = dict(row)
        item["body"] = body
        item["normalized_body"] = normalized_body
        item["body_hash"] = body_hash
        item["business_pool"] = pool
        item["categories"] = list(coerce_categories(row.get("categories")))
        admitted.append(item)

    stats.admitted = len(admitted)
    return admitted, stats


def allocate_domain_quotas(
    *,
    candidate_counts: Mapping[str, int],
    weight_counts: Mapping[str, int],
    target_total: int,
    base_quota: int,
) -> dict[str, int]:
    capped_target = max(0, min(int(target_total), sum(int(v) for v in candidate_counts.values())))
    quotas = {domain: min(int(candidate_counts.get(domain, 0)), int(base_quota)) for domain in candidate_counts}
    assigned = sum(quotas.values())
    if assigned >= capped_target:
        remaining = capped_target
        trimmed: dict[str, int] = {}
        for domain in DOMAIN_ORDER:
            if domain not in quotas:
                continue
            take = min(quotas[domain], remaining)
            trimmed[domain] = take
            remaining -= take
        return trimmed

    remainder = capped_target - assigned
    capacities = {
        domain: max(0, int(candidate_counts.get(domain, 0)) - quotas.get(domain, 0))
        for domain in candidate_counts
    }
    weighted_domains = [
        domain
        for domain in candidate_counts
        if capacities.get(domain, 0) > 0 and int(weight_counts.get(domain, 0)) > 0
    ]
    fallback_domains = [domain for domain in candidate_counts if capacities.get(domain, 0) > 0]
    active_domains = weighted_domains or fallback_domains
    total_weight = sum(max(1, int(weight_counts.get(domain, 0))) for domain in active_domains)
    provisional: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    extra_assigned = 0

    for domain in active_domains:
        weight = max(1, int(weight_counts.get(domain, 0)))
        share = remainder * weight / total_weight if total_weight > 0 else 0.0
        take = min(capacities[domain], int(math.floor(share)))
        provisional[domain] = take
        extra_assigned += take
        remainders.append((share - math.floor(share), domain))

    for domain, take in provisional.items():
        quotas[domain] += take

    still_left = remainder - extra_assigned
    for _fraction, domain in sorted(remainders, key=lambda item: (-item[0], DOMAIN_ORDER.index(item[1]))):
        if still_left <= 0:
            break
        if quotas[domain] >= int(candidate_counts.get(domain, 0)):
            continue
        quotas[domain] += 1
        still_left -= 1

    if still_left > 0:
        for domain in DOMAIN_ORDER:
            if still_left <= 0:
                break
            capacity = int(candidate_counts.get(domain, 0))
            while still_left > 0 and quotas.get(domain, 0) < capacity:
                quotas[domain] += 1
                still_left -= 1

    return {domain: int(quotas.get(domain, 0)) for domain in candidate_counts}


def rank_activation_comment(row: Mapping[str, Any]) -> tuple[float, int, int, int, int, int]:
    pool = str(row.get("business_pool") or "unscored").strip().lower()
    value_score = float(row.get("value_score") or 0.0)
    comment_score = int(row.get("score") or 0)
    post_score = int(row.get("post_score") or 0)
    post_num_comments = int(row.get("post_num_comments") or 0)
    body_len = len(str(row.get("normalized_body") or row.get("body") or ""))
    comment_id = int(row.get("id") or 0)
    return (
        value_score,
        _POOL_PRIORITY.get(pool, 0),
        comment_score,
        post_score,
        post_num_comments,
        body_len,
        -comment_id,
    )


def select_activation_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    weight_counts: Mapping[str, int],
    target_total: int,
    base_quota: int,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    by_domain: dict[str, list[dict[str, Any]]] = {domain: [] for domain in DOMAIN_ORDER}
    for raw_row in rows:
        row = dict(raw_row)
        categories = coerce_categories(row.get("categories"))
        domain = next((category for category in categories if category in DOMAIN_ORDER), "")
        if not domain:
            continue
        row["domain"] = domain
        by_domain[domain].append(row)

    candidate_counts = {domain: len(items) for domain, items in by_domain.items() if items}
    quotas = allocate_domain_quotas(
        candidate_counts=candidate_counts,
        weight_counts=weight_counts,
        target_total=target_total,
        base_quota=base_quota,
    )

    selected_by_domain: dict[str, list[dict[str, Any]]] = {}
    for domain, items in by_domain.items():
        if not items:
            continue
        ranked = sorted(items, key=rank_activation_comment, reverse=True)
        selected_by_domain[domain] = ranked[: quotas.get(domain, 0)]

    interleaved: list[dict[str, Any]] = []
    queues = {domain: deque(items) for domain, items in selected_by_domain.items() if items}
    while queues:
        for domain in DOMAIN_ORDER:
            queue = queues.get(domain)
            if queue is None:
                continue
            if queue:
                interleaved.append(queue.popleft())
            if not queue:
                queues.pop(domain, None)

    distribution = {domain: len(items) for domain, items in selected_by_domain.items()}
    return interleaved, quotas, distribution


def build_batch_plan(
    total_items: int,
    *,
    first_batch_size: int,
    batch_size: int,
) -> list[int]:
    remaining = max(0, int(total_items))
    if remaining == 0:
        return []

    plan: list[int] = []
    first = min(remaining, int(first_batch_size))
    plan.append(first)
    remaining -= first
    while remaining > 0:
        current = min(remaining, int(batch_size))
        plan.append(current)
        remaining -= current
    return plan


__all__ = [
    "CommentPrefilterStats",
    "DOMAIN_ORDER",
    "allocate_domain_quotas",
    "build_batch_plan",
    "build_comment_body_hash",
    "coerce_categories",
    "normalize_comment_body",
    "normalize_subreddit_key",
    "prefilter_comment_rows",
    "rank_activation_comment",
    "select_activation_rows",
]
