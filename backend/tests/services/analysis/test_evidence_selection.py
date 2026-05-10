from __future__ import annotations

from app.services.analysis.evidence_selection import (
    EvidenceSelectionInput,
    select_evidence_posts,
)


def test_select_evidence_posts_for_paypal_focus_keeps_issue_threads() -> None:
    posts = [
        {
            "id": "1",
            "title": "PayPal reversed the payment after delivery",
            "summary": "Customer received goods but payment got reversed.",
            "subreddit": "r/paypal",
        },
        {
            "id": "2",
            "title": "Stripe payouts are taking 5 days to hit my bank account",
            "summary": "Available balance shows late and hurts cash flow.",
            "subreddit": "r/stripe",
        },
        {
            "id": "3",
            "title": "Best CRM for small businesses?",
            "summary": "Need a generic tool recommendation for my startup.",
            "subreddit": "r/startups",
        },
    ]

    result = select_evidence_posts(
        posts,
        EvidenceSelectionInput(
            product_description="帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。",
            keywords=("paypal", "refund fee", "hold", "payout", "available balance"),
            preferred_communities=("r/paypal", "r/stripe"),
        ),
    )

    assert set(post["id"] for post in result.posts) == {"1", "2"}
    assert result.diagnostics.fallback_used is False


def test_select_evidence_posts_for_family_focus_keeps_sleep_and_handoff_threads() -> None:
    posts = [
        {
            "id": "1",
            "title": "Are all these newborn toys actually necessary?",
            "summary": "Trying to avoid overbuying for our newborn",
            "subreddit": "r/beyondthebump",
        },
        {
            "id": "2",
            "title": "Night feeding schedule and sleep log for a 2 week old",
            "summary": "Need a better tracker for feeding and naps",
            "subreddit": "r/NewParents",
        },
        {
            "id": "3",
            "title": "How do you hand off baby routine between parents at night?",
            "summary": "We keep losing track of who fed and changed the baby",
            "subreddit": "r/daddit",
        },
    ]

    result = select_evidence_posts(
        posts,
        EvidenceSelectionInput(
            product_description="我想研究新生儿夜奶、睡眠和家庭协作记录的真实痛点，看看有没有喂养追踪工具机会。",
            keywords=("newborn", "night feeding", "sleep log", "tracker", "handoff"),
            preferred_communities=("r/NewParents", "r/daddit"),
        ),
    )

    assert [post["id"] for post in result.posts] == ["2", "3"]


def test_select_evidence_posts_for_coffee_focus_keeps_grinder_threads() -> None:
    posts = [
        {
            "id": "1",
            "title": "What beans are you buying this week?",
            "summary": "Looking for light roast recommendations",
            "subreddit": "r/coffee",
        },
        {
            "id": "2",
            "title": "Dialing in espresso: grind size keeps drifting",
            "summary": "Same beans, different extraction every morning",
            "subreddit": "r/espresso",
        },
        {
            "id": "3",
            "title": "Why does my shot turn sour after changing grinder settings?",
            "summary": "Trying to log parameters and extraction time",
            "subreddit": "r/espresso",
        },
    ]

    result = select_evidence_posts(
        posts,
        EvidenceSelectionInput(
            product_description="我想研究浓缩咖啡磨豆和萃取参数总要重调的真实痛点，判断有没有配置助手机会。",
            keywords=("espresso", "grinder", "grind size", "extraction", "parameters"),
            preferred_communities=("r/espresso",),
        ),
    )

    assert [post["id"] for post in result.posts] == ["2", "3"]


def test_select_evidence_posts_falls_back_when_no_post_matches() -> None:
    posts = [
        {
            "id": "1",
            "title": "General startup bookkeeping workflow",
            "summary": "How do you categorize expenses every month?",
            "subreddit": "r/startups",
        }
    ]

    result = select_evidence_posts(
        posts,
        EvidenceSelectionInput(
            product_description="帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。",
            keywords=("paypal", "refund fee", "hold", "payout", "available balance"),
            preferred_communities=("r/paypal", "r/stripe"),
        ),
    )

    assert [post["id"] for post in result.posts] == ["1"]
    assert result.diagnostics.fallback_used is True
