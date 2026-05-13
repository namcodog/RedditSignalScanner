from __future__ import annotations

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.quality_contract import apply_hotpost_quality_contract


def _post(*, idx: int, title: str = "Sample title", subreddit: str = "r/test") -> Hotpost:
    return Hotpost(
        rank=idx,
        id=f"p{idx}",
        title=title,
        body_preview="preview",
        score=80,
        num_comments=12,
        heat_score=104,
        rant_score=8.0,
        rant_signals=["price"],
        subreddit=subreddit,
        author="user",
        reddit_url=f"https://www.reddit.com/r/test/comments/p{idx}",
        created_utc=0.0,
        signals=["price", "ux"],
        signal_score=8.0,
        top_comments=[
            HotpostComment(
                comment_fullname=f"t1_{idx}",
                author="user",
                body="This is a direct user quote.",
                score=9,
                permalink=f"/r/test/comments/p{idx}/_/{idx}",
            )
        ],
    )


def test_apply_hotpost_quality_contract_marks_trending_core_gaps_without_backfilling() -> None:
    payload = {
        "mode": "trending",
        "summary": "这波讨论在升温。",
        "evidence_count": 1,
        "topics": None,
        "trending_keywords": None,
        "top_quotes": None,
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="trending",
        top_posts=[_post(idx=1)],
        keywords=["creator", "economy"],
    )

    assert "missing_topics" in result.gaps
    assert "missing_time_trend" not in result.gaps
    assert "missing_topic_evidence" not in result.gaps
    assert result.payload.get("topics") is None
    assert result.payload.get("trending_keywords")
    assert result.payload.get("top_quotes")
    assert result.payload.get("next_steps", {}).get("suggested_keywords")


def test_apply_hotpost_quality_contract_marks_gaps_when_evidence_missing() -> None:
    payload = {
        "mode": "opportunity",
        "summary": "样本不足。",
        "evidence_count": 0,
        "unmet_needs": None,
        "market_opportunity": None,
        "top_quotes": None,
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="opportunity",
        top_posts=[],
        keywords=["test"],
    )

    assert "missing_evidence" in result.gaps
    assert "missing_top_quotes" in result.gaps
    assert "missing_unmet_needs" in result.gaps
    assert "missing_market_opportunity" in result.gaps
    assert any("质量合同未满配" in note for note in result.notes)


def test_apply_hotpost_quality_contract_marks_rant_core_gaps_without_backfilling() -> None:
    payload = {
        "mode": "rant",
        "summary": "用户在吐槽体验问题。",
        "evidence_count": 1,
        "pain_points": None,
        "migration_intent": None,
        "top_quotes": None,
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=1, title="Refund flow is broken")],
        keywords=["refund", "flow"],
    )

    assert result.payload.get("pain_points") is None
    assert "missing_pain_points" in result.gaps
    assert "missing_pain_voice" not in result.gaps
    assert "missing_migration_intent" in result.gaps


def test_apply_hotpost_quality_contract_skips_rant_summary_specificity_when_no_alignment_context() -> None:
    payload = {
        "mode": "rant",
        "summary": "大家在吐槽体验问题。",
        "evidence_count": 0,
        "pain_points": None,
        "migration_intent": None,
        "top_quotes": None,
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[],
        keywords=["notion", "ai"],
    )

    assert "missing_evidence" in result.gaps
    assert "missing_pain_points" in result.gaps
    assert "rant_summary_not_specific" not in result.gaps


def test_apply_hotpost_quality_contract_marks_opportunity_core_gaps_without_backfilling() -> None:
    payload = {
        "mode": "opportunity",
        "summary": "有人在求替代方案。",
        "evidence_count": 1,
        "unmet_needs": None,
        "market_opportunity": None,
        "top_quotes": None,
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="opportunity",
        top_posts=[_post(idx=1, title="Need a better scheduling tool")],
        keywords=["scheduling", "tool"],
    )

    assert result.payload.get("unmet_needs") is None
    assert result.payload.get("market_opportunity") is None
    assert "missing_unmet_needs" in result.gaps
    assert "missing_market_opportunity" in result.gaps


def test_apply_hotpost_quality_contract_replaces_weak_top_quotes_with_better_quotes() -> None:
    payload = {
        "mode": "opportunity",
        "summary": "有人在找替代方案。",
        "evidence_count": 1,
        "unmet_needs": [{"need": "Need better chargeback automation", "current_workarounds": []}],
        "market_opportunity": {"unmet_gap": "缺轻量风控工具"},
        "top_quotes": [
            {
                "quote": "Interested",
                "score": 1,
                "subreddit": "r/test",
                "url": "https://www.reddit.com/r/test/comments/p1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="opportunity",
        top_posts=[_post(idx=1, title="Need better chargeback tooling")],
        keywords=["chargeback", "tooling"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes
    assert all(item["quote"] != "Interested" for item in quotes)
    assert any("direct user quote" in item["quote"].lower() for item in quotes)


def test_apply_hotpost_quality_contract_enriches_top_quotes_with_traceable_meta() -> None:
    post = _post(idx=3, title="Premiere keeps crashing after export", subreddit="r/premiere")
    post.created_utc = 1710660000
    post.top_comments = [
        HotpostComment(
            comment_fullname="t1_trace",
            author="editor",
            body="Premiere crashes every time I export a longer timeline.",
            score=18,
            permalink="/r/premiere/comments/p3/_/trace",
        )
    ]
    payload = {
        "mode": "rant",
        "summary": "导出一长就崩。",
        "evidence_count": 1,
        "pain_points": [{"category": "导出就崩"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "Premiere crashes every time I export a longer timeline.",
                "score": 18,
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[post],
        keywords=["premiere", "crash", "export"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes
    assert quotes[0]["created_utc"] == 1710660000
    assert quotes[0]["thread_id"] == "p3"
    assert quotes[0]["quote_id"] == "p3:t1_trace"
    assert quotes[0]["thread_url"] == "https://www.reddit.com/r/test/comments/p3"


def test_apply_hotpost_quality_contract_prefers_explicit_complaint_over_advice_comment() -> None:
    post = _post(idx=4, title="Adobe Premiere keeps crashing on export", subreddit="r/premiere")
    post.top_comments = [
        HotpostComment(
            comment_fullname="t1_fix",
            author="helper",
            body="Double-check your plug-ins, try disabling them, and consider reseating the RAM first.",
            score=22,
            permalink="/r/premiere/comments/p4/_/fix",
        )
    ]
    payload = {
        "mode": "rant",
        "summary": "导出总崩。",
        "evidence_count": 1,
        "pain_points": [{"category": "导出总崩"}],
        "migration_intent": None,
        "top_quotes": [],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[post],
        keywords=["premiere", "crash", "export"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes
    assert "crashing on export" in quotes[0]["quote"].lower()
    assert "double-check" not in quotes[0]["quote"].lower()


def test_apply_hotpost_quality_contract_prefers_preview_when_title_is_fix_guide() -> None:
    post = _post(
        idx=40,
        title="How I fixed Premiere Pro 2025 loading very slowly",
        subreddit="r/premiere",
    )
    post.top_comments = []
    post.body_preview = (
        "Premiere keeps crashing every export and freezes the timeline on longer projects."
    )
    payload = {
        "mode": "rant",
        "summary": "summary",
        "evidence_count": 1,
        "pain_points": [],
        "top_quotes": [],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[post],
        keywords=["premiere", "crash"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes
    assert "keeps crashing every export" in quotes[0]["quote"].lower()
    assert "how i fixed premiere pro" not in quotes[0]["quote"].lower()


def test_apply_hotpost_quality_contract_filters_bot_and_discord_quotes() -> None:
    payload = {
        "mode": "rant",
        "summary": "卖家在抱怨 TikTok Shop 转化问题。",
        "evidence_count": 1,
        "pain_points": [{"category": "流量与转化脱节"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "[Join Our Discord Server!](https://discord.gg/demo)\nI am a bot, and this action was performed automatically. Please contact the moderators of this subreddit.",
                "score": 999,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=1, title="Low views and low conversion", subreddit="r/tiktokshop")],
        keywords=["tiktok", "conversion", "sales"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes
    assert all("discord" not in item["quote"].lower() for item in quotes)
    assert all("i am a bot" not in item["quote"].lower() for item in quotes)
    assert any("direct user quote" in item["quote"].lower() for item in quotes)


def test_apply_hotpost_quality_contract_keeps_stronger_quote_when_same_url_has_shorter_duplicate() -> None:
    payload = {
        "mode": "rant",
        "summary": "卖家在讨论有机销售和广告转化。",
        "evidence_count": 1,
        "pain_points": [{"category": "流量与转化脱节"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "Around 75% of my sales have been organic if not more. The cool thing about tiktok is that you don’t really need to pay for advertising.",
                "score": 5,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p1/_/c1",
            }
        ],
        "next_steps": {},
    }
    post = _post(idx=1, title="Organic beats paid for this shop", subreddit="r/tiktokshop")
    post.top_comments = [
        HotpostComment(
            comment_fullname="t1_full",
            author="user",
            body="Around 75% of my sales have been organic if not more. The cool thing about tiktok is that you don’t really need to pay for advertising. As long as you’re making content and being consistent, you can get sales.",
            score=5,
            permalink="/r/tiktokshop/comments/p1/_/c1",
        )
    ]

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[post],
        keywords=["tiktok", "conversion", "sales"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert len(quotes) == 1
    assert "As long as you’re making content and being consistent" in quotes[0]["quote"]


def test_apply_hotpost_quality_contract_preserves_specific_quote_why_important() -> None:
    payload = {
        "mode": "rant",
        "summary": "卖家在讨论广告和自然流量。",
        "evidence_count": 1,
        "pain_points": [{"category": "流量与转化脱节"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "Traffic is there but nobody buys.",
                "score": 8,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p2/_/c1",
                "why_important": "它把问题钉在成交层，不是单纯流量起伏。",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=2, title="Traffic is there but nobody buys", subreddit="r/tiktokshop")],
        keywords=["tiktok", "traffic", "sales"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes[0]["why_important"] == "它把问题钉在成交层，不是单纯流量起伏。"


def test_apply_hotpost_quality_contract_generates_rant_quote_why_important_when_missing() -> None:
    payload = {
        "mode": "rant",
        "summary": "卖家在讨论广告和自然流量。",
        "evidence_count": 1,
        "pain_points": [{"category": "流量与转化脱节"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "Around 75% of my sales have been organic if not more. You don’t really need to pay for advertising.",
                "score": 8,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p3/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=3, title="Organic beats paid for this shop", subreddit="r/tiktokshop")],
        keywords=["tiktok", "traffic", "sales"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes[0]["why_important"] is not None
    assert "自然流量" in quotes[0]["why_important"]


def test_apply_hotpost_quality_contract_drops_generic_quote_why_important_without_signal() -> None:
    payload = {
        "mode": "rant",
        "summary": "卖家在讨论广告和自然流量。",
        "evidence_count": 1,
        "pain_points": [{"category": "流量与转化脱节"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "Traffic is there but nobody buys.",
                "score": 8,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p4/_/c1",
                "why_important": "这说明这个问题值得关注。",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=4, title="Traffic is there but nobody buys", subreddit="r/tiktokshop")],
        keywords=["tiktok", "traffic", "sales"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes[0]["why_important"] is not None
    assert quotes[0]["why_important"] != "这说明这个问题值得关注。"
    assert "成交" in quotes[0]["why_important"]


def test_apply_hotpost_quality_contract_generates_specific_pay_to_play_quote_why() -> None:
    payload = {
        "mode": "rant",
        "summary": "卖家在讨论广告和自然流量。",
        "evidence_count": 1,
        "pain_points": [{"category": "流量与转化脱节"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "Yes you can still rely on organic reach but there will be a time when you have to pay to play, hint gmv max.",
                "score": 6,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p5/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=5, title="Organic reach may turn into pay to play", subreddit="r/tiktokshop")],
        keywords=["tiktok", "traffic", "sales"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes[0]["why_important"] is not None
    assert "买量" in quotes[0]["why_important"]


def test_apply_hotpost_quality_contract_generates_generic_product_quote_why() -> None:
    payload = {
        "mode": "rant",
        "summary": "咖啡机讨论在抱怨宣传不符。",
        "evidence_count": 1,
        "pain_points": [{"category": "为什么人看了不信"}],
        "migration_intent": None,
        "top_quotes": [
            {
                "quote": "They told me three times that yes, it does. I bought the machine. It does not have a three-way solenoid valve.",
                "score": 10,
                "subreddit": "r/espresso",
                "url": "https://www.reddit.com/r/espresso/comments/p6/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=6, title="Coffee machine is a scam", subreddit="r/espresso")],
        keywords=["coffee", "machine", "complaints"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes[0]["why_important"] is not None
    assert "被误导了" in quotes[0]["why_important"]


def test_apply_hotpost_quality_contract_flags_rant_summary_not_specific() -> None:
    payload = {
        "mode": "rant",
        "summary": "讨论很活跃，值得关注。",
        "evidence_count": 1,
        "pain_points": [{"category": "价格/费用", "description": "用户反复抱怨订阅费用不值。"}],
        "migration_intent": {"percentage": 0.2},
        "top_quotes": [
            {
                "quote": "This subscription is too expensive for what it does.",
                "score": 9,
                "subreddit": "r/test",
                "url": "https://www.reddit.com/r/test/comments/p7/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=7, title="Too expensive for basic features")],
        keywords=["subscription", "pricing"],
    )

    assert "rant_summary_not_specific" in result.gaps


def test_apply_hotpost_quality_contract_flags_rant_summary_off_topic() -> None:
    payload = {
        "mode": "rant",
        "summary": "Users repeatedly complain this is too expensive for the value.",
        "evidence_count": 1,
        "pain_points": [
            {
                "category": "售后/支持",
                "description": "用户集中抱怨客服慢、维修拖延。",
                "sample_quotes": ["Support has not replied for two weeks."],
            }
        ],
        "migration_intent": {"percentage": 0.2},
        "top_quotes": [
            {
                "quote": "Support has not replied for two weeks.",
                "score": 11,
                "subreddit": "r/test",
                "url": "https://www.reddit.com/r/test/comments/p8/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=8, title="Customer support response is too slow")],
        keywords=["support", "service"],
    )

    assert "rant_summary_off_topic" in result.gaps


def test_apply_hotpost_quality_contract_prioritizes_quote_matching_pain_category() -> None:
    payload = {
        "mode": "rant",
        "summary": "Users repeatedly complain this is too expensive for the value.",
        "evidence_count": 1,
        "pain_points": [{"category": "价格/费用", "sample_quotes": ["This costs too much."]}],
        "migration_intent": {"percentage": 0.1},
        "top_quotes": [
            {
                "quote": "Support has not replied for two weeks.",
                "score": 11,
                "subreddit": "r/test",
                "url": "https://www.reddit.com/r/test/comments/p9/_/c1",
            },
            {
                "quote": "This monthly plan is too expensive for basic features.",
                "score": 7,
                "subreddit": "r/test",
                "url": "https://www.reddit.com/r/test/comments/p9/_/c2",
            },
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=9, title="Plan price feels too high for what it offers")],
        keywords=["pricing", "subscription"],
    )

    quotes = result.payload.get("top_quotes") or []
    assert quotes
    assert "expensive" in quotes[0]["quote"].lower()


def test_apply_hotpost_quality_contract_accepts_human_summary_when_it_hits_pain_terms() -> None:
    payload = {
        "mode": "rant",
        "summary": "大家反复提到上手难、流程绕、界面不直觉，抱怨点集中在越用越费劲。",
        "evidence_count": 1,
        "pain_points": [{"category": "流程/体验太绕", "sample_quotes": ["This flow is too complicated."]}],
        "migration_intent": {"percentage": 0.1},
        "top_quotes": [
            {
                "quote": "This workflow is too complicated for daily use.",
                "score": 8,
                "subreddit": "r/test",
                "url": "https://www.reddit.com/r/test/comments/p10/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=10, title="Workflow became too hard to use")],
        keywords=["workflow", "ux"],
    )

    assert "rant_summary_not_specific" not in result.gaps


def test_apply_hotpost_quality_contract_accepts_business_rant_quote_alignment() -> None:
    payload = {
        "mode": "rant",
        "summary": "Traffic comes in but nobody buys, and conversion remains weak.",
        "evidence_count": 1,
        "pain_points": [
            {
                "category": "为什么人看了不买",
                "sample_quotes": ["Traffic is there but nobody buys."],
            }
        ],
        "migration_intent": {"percentage": 0.2},
        "top_quotes": [
            {
                "quote": "Traffic is there but nobody buys.",
                "score": 10,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p11/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=11, title="Traffic is high but orders stay near zero", subreddit="r/tiktokshop")],
        keywords=["tiktok", "traffic", "conversion", "sales"],
    )

    assert "rant_quote_off_topic" not in result.gaps


def test_apply_hotpost_quality_contract_accepts_business_rant_summary_specificity() -> None:
    payload = {
        "mode": "rant",
        "summary": "Traffic comes in but nobody buys, and conversion remains weak.",
        "evidence_count": 1,
        "pain_points": [
            {
                "category": "为什么人看了不买",
                "sample_quotes": ["Traffic is there but nobody buys."],
            }
        ],
        "migration_intent": {"percentage": 0.2},
        "top_quotes": [
            {
                "quote": "Traffic is there but nobody buys.",
                "score": 10,
                "subreddit": "r/tiktokshop",
                "url": "https://www.reddit.com/r/tiktokshop/comments/p12/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=12, title="Traffic is high but orders stay near zero", subreddit="r/tiktokshop")],
        keywords=["tiktok", "traffic", "conversion", "sales"],
    )

    assert "rant_summary_not_specific" not in result.gaps


def test_apply_hotpost_quality_contract_accepts_quote_alignment_when_subject_anchor_matches_keywords() -> None:
    payload = {
        "mode": "rant",
        "summary": "Claude voice mode interrupts constantly and drops context.",
        "evidence_count": 1,
        "pain_points": [
            {
                "category": "价格/费用",
                "sample_quotes": ["This subscription is too expensive."],
            }
        ],
        "migration_intent": {"percentage": 0.1},
        "top_quotes": [
            {
                "quote": "The worst thing about Claude is voice mode: it interrupts constantly and drops off unlike ChatGPT.",
                "score": 9,
                "subreddit": "r/openai",
                "url": "https://www.reddit.com/r/openai/comments/p13/_/c1",
            }
        ],
        "next_steps": {},
    }

    result = apply_hotpost_quality_contract(
        payload=payload,
        mode="rant",
        top_posts=[_post(idx=13, title="Claude voice mode keeps interrupting", subreddit="r/openai")],
        keywords=["codex", "claude", "voice"],
    )

    assert "rant_quote_off_topic" not in result.gaps
