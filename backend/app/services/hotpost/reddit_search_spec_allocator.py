from __future__ import annotations


def _round_robin_take(groups: list[list[str]], limit: int) -> list[str]:
    selected: list[str] = []
    budget = max(limit, 0)
    lanes = [list(group) for group in groups if group]
    while budget > 0 and any(lanes):
        for lane in lanes:
            if not lane or budget <= 0:
                continue
            selected.append(str(lane.pop(0)))
            budget -= 1
    return selected


def allocate_search_inputs(
    subreddits: list[str],
    keyword_buckets: dict[str, list[str]],
    bucket_priority: list[str],
    templates: list[str],
    *,
    subreddit_limit: int,
    keywords_per_bucket: int,
    template_limit: int,
    spec_limit: int,
) -> tuple[list[str], list[str]]:
    selected_subreddits = subreddits[: max(subreddit_limit, 1)]
    cost = len(selected_subreddits)
    if cost == 0:
        return selected_subreddits, []

    query_budget = max(spec_limit, 0) // cost
    if query_budget <= 0:
        return selected_subreddits, []

    template_pool = list(templates[: max(template_limit * 4, 0)])
    template_slots = 0
    if template_pool:
        template_slots = min(
            len(template_pool),
            max(1, min(max(template_limit, 0), query_budget // 2 or 1)),
        )
    keyword_slots = max(query_budget - template_slots, 0)
    keyword_groups = [
        list(keyword_buckets.get(bucket) or [])[: max(keywords_per_bucket, 0)]
        for bucket in bucket_priority
    ]
    selected_queries = _round_robin_take(keyword_groups, keyword_slots)
    if len(selected_queries) < query_budget:
        remaining_templates = template_pool[: query_budget - len(selected_queries)]
        selected_queries.extend(str(item) for item in remaining_templates)
    return selected_subreddits, selected_queries[:query_budget]


def allocate_listing_inputs(
    subreddits: list[str],
    listing_rules: list[tuple[str, str]],
    *,
    subreddit_limit: int,
    spec_limit: int,
) -> tuple[list[str], list[tuple[str, str]]]:
    selected_subreddits = subreddits[: max(subreddit_limit, 1)]
    selected_rules: list[tuple[str, str]] = []
    budget = max(spec_limit, 0)
    for rule in listing_rules:
        cost = len(selected_subreddits)
        if cost == 0 or budget < cost:
            break
        selected_rules.append(rule)
        budget -= cost
    return selected_subreddits, selected_rules


__all__ = ["allocate_listing_inputs", "allocate_search_inputs"]
