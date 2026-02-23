from __future__ import annotations

from app.services.hotpost.report_export import export_markdown_report


def test_export_markdown_report_contains_sections() -> None:
    data = {
        "query": "AI tools",
        "mode": "trending",
        "summary": "一行结论",
        "confidence": "high",
        "evidence_count": 3,
        "community_distribution": {"r/x": "50%"},
        "sentiment_overview": {"positive": 0.5, "neutral": 0.5, "negative": 0.0},
        "topics": [
            {
                "rank": 1,
                "topic": "Topic A",
                "time_trend": "新兴🆕",
                "heat_score": 10,
                "key_takeaway": "takeaway",
                "evidence": [
                    {
                        "title": "Post A",
                        "score": 10,
                        "comments": 2,
                        "subreddit": "r/x",
                        "url": "https://www.reddit.com/r/x/comments/a",
                        "key_quote": "quote",
                    }
                ],
            }
        ],
        "top_posts": [
            {
                "rank": 1,
                "id": "p1",
                "title": "Post A",
                "body_preview": "body preview",
                "score": 10,
                "num_comments": 2,
                "heat_score": 14,
                "subreddit": "r/x",
                "author": "user",
                "reddit_url": "https://www.reddit.com/r/x/comments/a",
                "created_utc": 0,
                "signals": ["signal"],
                "signal_score": 1.0,
                "why_relevant": "important",
                "top_comments": [
                    {"author": "c1", "body": "comment body", "score": 5, "permalink": "https://www.reddit.com/r/x/comments/a#c1"}
                ],
            }
        ],
        "reliability_note": "样本有限",
    }

    md = export_markdown_report(data)
    assert "## 🔥 热点话题" in md
    assert "🗣️ 神评论" in md
    assert "reddit.com" in md


def test_export_markdown_report_rant_mode_sections() -> None:
    data = {
        "query": "Adobe 口碑",
        "mode": "rant",
        "summary": "负面反馈集中在订阅价格",
        "confidence": "high",
        "evidence_count": 12,
        "community_distribution": {"r/adobe": "50%"},
        "sentiment_overview": {"positive": 0.1, "neutral": 0.2, "negative": 0.7},
        "rant_intensity": {"strong": 0.4, "medium": 0.4, "weak": 0.2},
        "pain_points": [
            {
                "rank": 1,
                "category": "定价策略",
                "severity": "high",
                "mentions": 5,
                "percentage": 0.4,
                "key_takeaway": "价格过高",
                "user_voice": "too expensive",
                "business_implication": "流失风险",
                "evidence_posts": [
                    {
                        "title": "Why I'm leaving",
                        "subreddit": "r/adobe",
                        "score": 10,
                        "num_comments": 2,
                        "heat_score": 14,
                        "rant_score": 80,
                        "signals": ["expensive"],
                        "reddit_url": "https://www.reddit.com/r/adobe/comments/a",
                        "top_comments": [
                            {"author": "c1", "body": "same here", "score": 3, "permalink": "https://www.reddit.com/r/adobe/comments/a#c1"}
                        ],
                    }
                ],
            }
        ],
        "migration_intent": {
            "total_mentions": 3,
            "percentage": 0.25,
            "status_distribution": {"already_left": 0.2, "considering": 0.6, "staying": 0.2},
            "destinations": [{"name": "Affinity", "mentions": 2, "sentiment": "positive"}],
            "key_quote": "switched already",
        },
        "competitor_mentions": [
            {
                "name": "Affinity",
                "mentions": 2,
                "sentiment": "positive",
                "sentiment_score": 0.7,
                "common_praise": ["one-time fee"],
                "common_complaint": ["missing plugins"],
                "vs_adobe": "better pricing",
                "evidence_quote": "Affinity is cheaper",
            }
        ],
        "top_rants": [
            {
                "rank": 1,
                "title": "Cancellation is a scam",
                "subreddit": "r/adobe",
                "score": 20,
                "num_comments": 5,
                "heat_score": 30,
                "rant_score": 90,
                "rant_signals": ["scam"],
                "body_preview": "they hide cancel...",
                "why_important": "top rant",
                "reddit_url": "https://www.reddit.com/r/adobe/comments/b",
                "top_comments": [],
            }
        ],
        "reliability_note": "样本有限",
    }

    md = export_markdown_report(data)
    assert "痛点挖掘报告" in md
    assert "核心痛点" in md
    assert "迁移意向" in md
    assert "竞品分析" in md
    assert "Top 吐槽帖" in md


def test_export_markdown_report_opportunity_mode_sections() -> None:
    data = {
        "query": "AI 视频工具",
        "mode": "opportunity",
        "summary": "用户需求集中在自动字幕",
        "confidence": "medium",
        "evidence_count": 8,
        "community_distribution": {"r/VideoEditing": "60%"},
        "need_urgency": {"urgent": 0.3, "moderate": 0.5, "casual": 0.2},
        "unmet_needs": [
            {
                "rank": 1,
                "need": "自动字幕",
                "urgency": "high",
                "mentions": 4,
                "me_too_count": 10,
                "price_range": "$20-50",
                "key_takeaway": "节省时间",
                "user_voice": "need subtitles",
                "current_workarounds": [{"name": "manual", "satisfaction": "low"}],
                "evidence_posts": [
                    {
                        "title": "Need subtitles tool",
                        "subreddit": "r/VideoEditing",
                        "score": 12,
                        "num_comments": 3,
                        "heat_score": 18,
                        "reddit_url": "https://www.reddit.com/r/VideoEditing/comments/a",
                        "top_comments": [],
                    }
                ],
            }
        ],
        "existing_tools": [
            {
                "name": "Descript",
                "mentions": 3,
                "sentiment": "mixed",
                "sentiment_score": 0.3,
                "common_praise": ["fast"],
                "common_complaint": ["expensive"],
                "gap_analysis": "translation weak",
            }
        ],
        "user_segments": [
            {
                "segment": "YouTuber",
                "percentage": "40%",
                "key_need": "字幕",
                "price_sensitivity": "中",
                "typical_quote": "need it",
            }
        ],
        "market_opportunity": {
            "strength": "medium",
            "unmet_gap": "一站式字幕",
            "demand_signal": "high",
            "competition_level": "medium",
            "recommendation": "先做字幕",
        },
        "top_discovery_posts": [
            {
                "rank": 1,
                "title": "Tool for subtitles?",
                "subreddit": "r/VideoEditing",
                "score": 14,
                "num_comments": 4,
                "heat_score": 22,
                "resonance_count": 5,
                "body_preview": "looking for tool",
                "why_important": "clear need",
                "reddit_url": "https://www.reddit.com/r/VideoEditing/comments/b",
            }
        ],
        "reliability_note": "样本有限",
    }

    md = export_markdown_report(data)
    assert "机会发现报告" in md
    assert "核心需求" in md
    assert "现有工具" in md
    assert "用户画像" in md
    assert "市场机会" in md
    assert "Top 发现帖" in md
