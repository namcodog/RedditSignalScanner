from __future__ import annotations

from app.services.crawl.comments_parser import parse_morechildren_things


def test_parse_morechildren_returns_comments_and_more_ids() -> None:
    payload = {
        "json": {
            "data": {
                "things": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c3",
                            "body": "Another reply",
                            "author": "u3",
                            "author_fullname": "t2_u3",
                            "created_utc": 1002,
                            "score": 2,
                            "parent_id": "t1_c1",
                        },
                    },
                    {"kind": "more", "data": {"children": ["c4", "c5"]}},
                ]
            }
        }
    }

    comments, mores = parse_morechildren_things(payload)
    assert [c["id"] for c in comments] == ["c3"]
    assert mores == [["c4", "c5"]]

