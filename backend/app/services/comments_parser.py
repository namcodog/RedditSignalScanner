from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _extract_comment_node(node: Dict[str, Any], depth: int) -> Dict[str, Any]:
    d = node.get("data", {})
    return {
        "id": d.get("id"),
        "body": d.get("body"),
        "author": d.get("author"),
        "author_id": d.get("author_fullname"),
        "created_utc": d.get("created_utc"),
        "score": d.get("score"),
        "parent_id": d.get("parent_id"),
        "depth": depth,
        "is_submitter": d.get("is_submitter"),
        "distinguished": d.get("distinguished"),
        "edited": bool(d.get("edited") not in (False, None, 0)),
        "permalink": d.get("permalink"),
        "removed_by_category": d.get("removed_by_category"),
        "awards_count": (d.get("total_awards_received") or 0),
    }


def flatten_reddit_comments(listing: Any, *, max_items: int | None = None) -> List[Dict[str, Any]]:
    """Flatten Reddit /comments response into a simple list of dicts.

    Args:
        listing: The second element of the `/comments/{id}.json` response or its `data.children` list
        max_items: Maximum number of comment entries to return (approximate; stops pre-order traversal)
    """
    # Accept both the full listing (dict with data.children) or a children list
    children: Iterable[Dict[str, Any]]
    if isinstance(listing, dict):
        children = listing.get("data", {}).get("children", [])
    else:
        children = list(listing)

    out: List[Dict[str, Any]] = []

    def walk(nodes: Iterable[Dict[str, Any]], depth: int) -> None:
        nonlocal out
        for node in nodes:
            kind = node.get("kind")
            if kind == "more":
                # ignore placeholders in Top-N mode (full mode should call /api/morechildren)
                continue
            if kind != "t1":  # not a comment
                continue
            out.append(_extract_comment_node(node, depth))
            if max_items is not None and len(out) >= max_items:
                return
            replies = node.get("data", {}).get("replies") or {}
            if isinstance(replies, dict):
                walk(replies.get("data", {}).get("children", []), depth + 1)
                if max_items is not None and len(out) >= max_items:
                    return

    walk(children, 0)
    return out


def parse_morechildren_things(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[List[str]]]:
    """Parse /api/morechildren response into (comments, more_children_id_lists).

    The response schema (simplified):
    {
      "json": {
        "data": {
          "things": [ {"kind": "t1", "data": {...}}, {"kind": "more", "data": {"children": ["id1", ...]} } ]
        }
      }
    }
    """
    comments: List[Dict[str, Any]] = []
    mores: List[List[str]] = []

    try:
        things = payload.get("json", {}).get("data", {}).get("things", [])
    except Exception:
        things = []

    for thing in things:
        kind = thing.get("kind")
        data = thing.get("data", {})
        if kind == "t1":
            comments.append(
                {
                    "id": data.get("id"),
                    "body": data.get("body"),
                    "author": data.get("author"),
                    "author_id": data.get("author_fullname"),
                    "created_utc": data.get("created_utc"),
                    "score": data.get("score"),
                    "parent_id": data.get("parent_id"),
                    # depth is not provided in morechildren; caller can recompute if needed
                    "depth": 0,
                    "is_submitter": data.get("is_submitter"),
                    "distinguished": data.get("distinguished"),
                    "edited": bool(data.get("edited") not in (False, None, 0)),
                    "permalink": data.get("permalink"),
                    "removed_by_category": data.get("removed_by_category"),
                    "awards_count": (data.get("total_awards_received") or 0),
                }
            )
        elif kind == "more":
            children = data.get("children") or []
            if children:
                mores.append([str(x) for x in children])

    return comments, mores


def compute_smart_shallow_limits(
    *,
    total_limit: int,
    base_top_limit: int = 30,
    base_new_limit: int = 20,
    base_reply_top_limit: int = 15,
    reply_per_top: int = 1,
) -> Tuple[int, int, int]:
    if total_limit <= 0:
        return (
            max(1, int(base_top_limit)),
            max(0, int(base_new_limit)),
            max(0, int(base_reply_top_limit)),
        )

    base_top = max(1, int(base_top_limit))
    base_new = max(0, int(base_new_limit))
    reply_count = max(0, int(reply_per_top))
    base_reply_top = max(0, min(int(base_reply_top_limit), base_top))

    base_total = base_top + base_new + base_reply_top * reply_count
    if total_limit >= base_total:
        return base_top, base_new, base_reply_top

    ratio = base_new / base_top if base_top else 0.0
    reply_ratio = base_reply_top / base_top if base_top else 0.0
    denom = 1.0 + ratio + reply_ratio * reply_count
    top_limit = max(1, int(total_limit / denom))
    new_limit = max(0, int(round(top_limit * ratio)))
    reply_top_limit = max(0, min(int(round(top_limit * reply_ratio)), top_limit))

    while (
        top_limit + new_limit + reply_top_limit * reply_count > total_limit
        and top_limit > 1
    ):
        top_limit -= 1
        reply_top_limit = max(0, min(reply_top_limit, top_limit))
    while (
        top_limit + new_limit + reply_top_limit * reply_count > total_limit
        and new_limit > 0
    ):
        new_limit -= 1
    while (
        top_limit + new_limit + reply_top_limit * reply_count > total_limit
        and reply_top_limit > 0
    ):
        reply_top_limit -= 1

    return top_limit, new_limit, reply_top_limit


def _comment_score(comment: Dict[str, Any]) -> int:
    try:
        return int(comment.get("score") or 0)
    except (TypeError, ValueError):
        return 0


def _comment_created(comment: Dict[str, Any]) -> int:
    try:
        return int(comment.get("created_utc") or 0)
    except (TypeError, ValueError):
        return 0


def _is_top_level(comment: Dict[str, Any]) -> bool:
    depth = comment.get("depth")
    if isinstance(depth, int):
        return depth == 0
    parent = str(comment.get("parent_id") or "")
    return parent.startswith("t3_")


def _build_replies_index(comments: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    replies: Dict[str, List[Dict[str, Any]]] = {}
    for comment in comments:
        parent = str(comment.get("parent_id") or "")
        if not parent.startswith("t1_"):
            continue
        parent_id = parent[3:]
        if not parent_id:
            continue
        replies.setdefault(parent_id, []).append(comment)

    for parent_id, items in replies.items():
        items.sort(
            key=lambda c: (_comment_score(c), _comment_created(c)),
            reverse=True,
        )
        replies[parent_id] = items
    return replies


def select_smart_shallow_comments(
    *,
    top_comments: List[Dict[str, Any]],
    new_comments: List[Dict[str, Any]],
    top_limit: int,
    new_limit: int,
    reply_top_limit: int,
    reply_per_top: int = 1,
    total_limit: int | None = None,
) -> List[Dict[str, Any]]:
    """Pick a smart shallow subset: top-level + best replies + newest."""
    top_limit = max(0, int(top_limit))
    new_limit = max(0, int(new_limit))
    reply_per_top = max(0, int(reply_per_top))
    reply_top_limit = max(0, int(reply_top_limit))
    if total_limit is not None:
        total_limit = max(1, int(total_limit))

    top_level_top = [c for c in top_comments if _is_top_level(c)]
    top_level_top.sort(
        key=lambda c: (_comment_score(c), _comment_created(c)),
        reverse=True,
    )

    top_level_new = [c for c in new_comments if _is_top_level(c)]
    top_level_new.sort(key=_comment_created, reverse=True)

    replies_index = _build_replies_index([*top_comments, *new_comments])

    selected: List[Dict[str, Any]] = []
    used_ids: set[str] = set()

    def _add(comment: Dict[str, Any]) -> None:
        cid = str(comment.get("id") or "")
        if not cid or cid in used_ids:
            return
        selected.append(comment)
        used_ids.add(cid)

    for idx, top in enumerate(top_level_top[:top_limit]):
        _add(top)
        if reply_per_top > 0 and idx < reply_top_limit:
            replies = replies_index.get(str(top.get("id") or ""), [])
            for reply in replies[:reply_per_top]:
                _add(reply)

    if total_limit is None or len(selected) < total_limit:
        for newest in top_level_new[:new_limit]:
            _add(newest)
            if total_limit is not None and len(selected) >= total_limit:
                break

    if total_limit is not None and len(selected) < total_limit:
        for newest in top_level_new[new_limit:]:
            _add(newest)
            if len(selected) >= total_limit:
                break

    if total_limit is not None and len(selected) > total_limit:
        selected = selected[:total_limit]

    return selected
