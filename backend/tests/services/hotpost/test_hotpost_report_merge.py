from __future__ import annotations

from app.services.hotpost.report_llm import apply_hotpost_llm_annotations, merge_hotpost_llm_report


def test_merge_hotpost_llm_report_overrides_summary_and_topics() -> None:
    base = {
        "summary": "fallback",
        "confidence": "high",
        "evidence_count": 30,
        "topics": None,
    }
    llm_report = {
        "summary": "llm summary",
        "topics": [
            {
                "rank": 1,
                "topic": "AI Agents",
                "heat_score": 99,
                "time_trend": "新兴🆕",
                "key_takeaway": "hot",
                "evidence": [],
            }
        ],
        "confidence": "low",
        "evidence_count": 1,
    }
    merged = merge_hotpost_llm_report(base, llm_report)
    assert merged["summary"] == "llm summary"
    assert merged["topics"] == llm_report["topics"]
    # 统计值不应被 LLM 覆盖
    assert merged["confidence"] == "high"
    assert merged["evidence_count"] == 30


def test_merge_hotpost_llm_report_keeps_base_when_missing() -> None:
    base = {"summary": "fallback", "trending_keywords": ["ai"], "community_distribution": {"r/x": "50%"}}
    llm_report = {"summary": None}
    merged = merge_hotpost_llm_report(base, llm_report)
    assert merged["summary"] == "fallback"
    assert merged["trending_keywords"] == ["ai"]
    assert merged["community_distribution"] == {"r/x": "50%"}


def test_apply_hotpost_llm_annotations_maps_evidence_and_relevance() -> None:
    base = {
        "top_posts": [
            {
                "id": "p1",
                "title": "Post 1",
                "score": 10,
                "num_comments": 2,
                "subreddit": "r/x",
                "reddit_url": "https://www.reddit.com/r/x/comments/p1",
                "top_comments": [{"body": "quote-1"}],
            },
            {
                "id": "p2",
                "title": "Post 2",
                "score": 5,
                "num_comments": 1,
                "subreddit": "r/y",
                "reddit_url": "https://www.reddit.com/r/y/comments/p2",
                "top_comments": [],
            },
        ],
        "topics": [
            {
                "rank": 1,
                "topic": "Topic A",
                "heat_score": 42,
                "time_trend": "新兴🆕",
                "key_takeaway": "takeaway",
                "evidence_post_ids": ["p2", "p1"],
            }
        ],
    }
    llm_report = {
        "topics": base["topics"],
        "post_annotations": {"p1": {"why_relevant": "重要原因"}},
    }

    merged = apply_hotpost_llm_annotations(base, llm_report)
    topic = merged["topics"][0]
    assert "evidence_post_ids" not in topic
    assert len(topic["evidence"]) == 2
    assert len(topic["evidence_posts"]) == 2
    assert topic["evidence"][0]["url"] == "https://www.reddit.com/r/y/comments/p2"
    assert topic["evidence_posts"][0]["reddit_url"] == "https://www.reddit.com/r/y/comments/p2"
    assert topic["evidence"][1]["key_quote"] == "quote-1"
    assert merged["top_posts"][0]["why_relevant"] == "重要原因"
