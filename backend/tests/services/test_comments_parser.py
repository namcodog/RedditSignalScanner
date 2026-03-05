from __future__ import annotations

from app.services.crawl.comments_parser import flatten_reddit_comments


def test_flatten_reddit_comments_basic() -> None:
    payload = {
        "data": {
            "children": [
                {
                    "kind": "t1",
                    "data": {
                        "id": "c1",
                        "body": "Top comment",
                        "author": "u1",
                        "author_fullname": "t2_u1",
                        "created_utc": 1000,
                        "score": 10,
                        "permalink": "/r/test/comments/xyz/c1/",
                        "replies": {
                            "data": {
                                "children": [
                                    {
                                        "kind": "t1",
                                        "data": {
                                            "id": "c2",
                                            "body": "Reply",
                                            "author": "u2",
                                            "author_fullname": "t2_u2",
                                            "created_utc": 1001,
                                            "score": 5,
                                            "permalink": "/r/test/comments/xyz/c2/",
                                        },
                                    }
                                ]
                            }
                        },
                    },
                },
                {"kind": "more", "data": {"count": 10, "children": ["c3", "c4"]}},
            ]
        }
    }

    out = flatten_reddit_comments(payload, max_items=None)
    ids = [c["id"] for c in out]
    assert ids == ["c1", "c2"]
    depths = [c["depth"] for c in out]
    assert depths == [0, 1]

