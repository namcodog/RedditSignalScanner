from __future__ import annotations

from app.schemas.hotpost import Hotpost
from app.services.hotpost.rant_action_rules import (
    rewrite_rant_action,
    should_replace_rant_post_relevant,
)


def test_rewrite_rant_action_turns_intent_noise_into_funnel_action() -> None:
    rewritten = rewrite_rant_action(
        {"category": "流量质量与购买意图脱节"},
        "先处理「购买意图」：检查落地页和购买引导",
        get_payload_value=lambda item, field: item.get(field),
    )

    assert rewritten == "先别再只看点击率，先确认广告带来的流量是不是想买的人。"


def test_should_replace_rant_post_relevant_rejects_non_cjk_placeholder() -> None:
    post = Hotpost(
        rank=1,
        id="p1",
        title="Example",
        body_preview="Example body",
        score=5,
        num_comments=1,
        heat_score=1,
        rant_score=1.0,
        rant_signals=[],
        subreddit="r/test",
        author="user",
        reddit_url="https://www.reddit.com/r/test/comments/p1",
        created_utc=0.0,
        signals=[],
        signal_score=1.0,
        why_relevant="direct keyword hit",
        top_comments=[],
    )

    assert should_replace_rant_post_relevant(post.why_relevant, generated="这条帖子命中了真实抱怨场景。")
