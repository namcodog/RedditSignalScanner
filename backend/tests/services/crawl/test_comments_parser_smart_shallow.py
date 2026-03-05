from __future__ import annotations

from app.services.crawl.comments_parser import (
    compute_smart_shallow_limits,
    select_smart_shallow_comments,
)


def _comment(
    *,
    cid: str,
    parent_id: str,
    score: int,
    created_utc: int,
    depth: int,
) -> dict[str, object]:
    return {
        "id": cid,
        "parent_id": parent_id,
        "score": score,
        "created_utc": created_utc,
        "depth": depth,
        "body": f"body-{cid}",
    }


def test_compute_smart_shallow_limits_scales_down() -> None:
    top_limit, new_limit, reply_top_limit = compute_smart_shallow_limits(
        total_limit=50,
        base_top_limit=30,
        base_new_limit=20,
        base_reply_top_limit=15,
        reply_per_top=1,
    )

    assert top_limit == 23
    assert new_limit == 15
    assert reply_top_limit == 12
    assert top_limit + new_limit + reply_top_limit == 50


def test_select_smart_shallow_comments_picks_top_and_replies_and_new() -> None:
    top_comments = [
        _comment(cid="c1", parent_id="t3_post", score=100, created_utc=1000, depth=0),
        _comment(cid="r1", parent_id="t1_c1", score=5, created_utc=1001, depth=1),
        _comment(cid="r2", parent_id="t1_c1", score=20, created_utc=1002, depth=1),
        _comment(cid="c2", parent_id="t3_post", score=50, created_utc=900, depth=0),
        _comment(cid="r3", parent_id="t1_c2", score=3, created_utc=901, depth=1),
    ]
    new_comments = [
        _comment(cid="c3", parent_id="t3_post", score=1, created_utc=2000, depth=0),
        _comment(cid="c1", parent_id="t3_post", score=100, created_utc=1000, depth=0),
    ]

    selected = select_smart_shallow_comments(
        top_comments=top_comments,
        new_comments=new_comments,
        top_limit=2,
        new_limit=2,
        reply_top_limit=1,
        reply_per_top=1,
        total_limit=10,
    )

    ids = [str(item.get("id")) for item in selected]
    assert ids == ["c1", "r2", "c2", "c3"]


def test_select_smart_shallow_comments_fills_with_new_top_level() -> None:
    top_comments = [
        _comment(cid="c1", parent_id="t3_post", score=100, created_utc=1000, depth=0),
        _comment(cid="r1", parent_id="t1_c1", score=5, created_utc=1001, depth=1),
    ]
    new_comments = [
        _comment(cid="c_new1", parent_id="t3_post", score=1, created_utc=2000, depth=0),
        _comment(cid="c_new2", parent_id="t3_post", score=1, created_utc=1999, depth=0),
    ]

    selected = select_smart_shallow_comments(
        top_comments=top_comments,
        new_comments=new_comments,
        top_limit=1,
        new_limit=0,
        reply_top_limit=1,
        reply_per_top=1,
        total_limit=3,
    )

    ids = [str(item.get("id")) for item in selected]
    assert ids == ["c1", "r1", "c_new1"]
