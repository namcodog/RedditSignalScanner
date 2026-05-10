from __future__ import annotations

from app.schemas.hotpost import Hotpost
from app.services.hotpost.rant_signal_rules import (
    build_rant_post_why,
    build_rant_summary,
    build_voice_rant_summary,
)


def test_build_rant_summary_keeps_generic_trust_gap_out_of_conversion_language() -> None:
    summary = build_rant_summary(
        {
            "summary": "Users say the support told me it had HEPA but the product does not have it.",
            "pain_points": [
                {
                    "key_takeaway": "客服承诺和到手体验对不上",
                    "user_voice": "Support told me it had HEPA but the product does not have it.",
                }
            ],
        },
        keywords=["air", "purifier"],
        query_family="generic_complaint_discovery",
        primary_friction="trust_gap",
    )

    assert summary == "大家最不满的不是某个小故障，而是宣传、客服承诺和到手体验经常对不上。"


def test_build_voice_rant_summary_uses_quote_for_thin_specific_issue_sample() -> None:
    summary = build_voice_rant_summary(
        {
            "evidence_count": 1,
            "top_quotes": [{"quote": "It keeps rewriting my notes into vague fluff that says nothing."}],
        },
        keywords=["notion", "ai"],
        query_family="specific_issue",
    )

    assert summary == "目前只抓到少量讨论，代表性抱怨是：It keeps rewriting my notes into vague fluff that says nothing."


def test_build_rant_post_why_prefers_channel_restriction_signal() -> None:
    post = Hotpost(
        rank=1,
        id="p1",
        title="TikTok ads keep rejecting my supplement and I can't scale it",
        body_preview="Policies say restricted items need authorization and paid traffic stops there.",
        score=35,
        num_comments=8,
        heat_score=18,
        rant_score=14.0,
        rant_signals=["restricted", "paid"],
        subreddit="r/TikTokAds",
        author="user",
        reddit_url="https://www.reddit.com/r/tiktokads/comments/p1",
        created_utc=0.0,
        signals=["restricted", "ads"],
        signal_score=12.0,
        top_comments=[],
    )

    assert build_rant_post_why(post) == "这条帖子暴露的不是素材好不好，而是这类商品在主流广告渠道本身就受限。"
