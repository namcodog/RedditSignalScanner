from __future__ import annotations

import time

from app.schemas.hotpost import Hotpost
from app.services.hotpost.mode_contract import apply_hotpost_mode_contract


def _post(*, idx: int, title: str, body: str, subreddit: str = "r/saas") -> Hotpost:
    return Hotpost(
        rank=idx,
        id=f"p{idx}",
        title=title,
        body_preview=body,
        score=10,
        num_comments=3,
        heat_score=16,
        rant_score=8.0,
        rant_signals=["issue"],
        subreddit=subreddit,
        author="user",
        reddit_url=f"https://www.reddit.com/r/test/comments/p{idx}",
        created_utc=time.time(),
        signals=["issue"],
        signal_score=8.0,
        top_comments=[],
    )


def test_apply_hotpost_mode_contract_marks_preview_for_small_but_real_opportunity_hit() -> None:
    payload = {
        "unmet_needs": [{"need": "Need better chargeback response software"}],
        "top_quotes": [{"quote": "We keep losing chargeback response cases even after uploading evidence.", "url": "https://reddit.com/x"}],
    }
    posts = [
        _post(
            idx=1,
            title="Shopify chargeback response workflow is too manual",
            body="We keep losing disputes because evidence upload is still manual.",
        )
    ]

    _, state, reasons, note, _metrics = apply_hotpost_mode_contract(
        mode="opportunity",
        payload=payload,
        top_posts=posts,
        positive_intent_terms=["software", "response"],
        domain_terms=["chargeback", "dispute"],
        raw_posts=1,
        relevance_filtered=0,
    )

    assert state == "preview"
    assert any(reason.startswith("preview:") for reason in reasons)
    assert "先保留最强信号" in note


def test_apply_hotpost_mode_contract_clears_primary_fields_on_no_hit() -> None:
    payload = {
        "unmet_needs": [{"need": "Need homework helper"}],
        "market_opportunity": {"unmet_gap": "generic"},
        "existing_tools": [{"name": "tool"}],
    }

    cleaned, state, reasons, _note, _metrics = apply_hotpost_mode_contract(
        mode="opportunity",
        payload=payload,
        top_posts=[],
        positive_intent_terms=["software"],
        domain_terms=["chargeback"],
        raw_posts=1,
        relevance_filtered=0,
    )

    assert state == "no_hit"
    assert "hit:evidence_posts" in reasons
    assert cleaned["unmet_needs"] == []
    assert cleaned["market_opportunity"] is None
    assert cleaned["existing_tools"] == []


def test_apply_hotpost_mode_contract_allows_preview_for_single_rant_anchor_hit() -> None:
    payload = {
        "pain_points": [],
        "top_quotes": [{"quote": "Traffic is there, but no sales are coming through.", "url": "https://reddit.com/x"}],
    }
    posts = [
        _post(
            idx=1,
            title="TikTok Shop has fallen off",
            body="Traffic is still there, but sales have dried up.",
            subreddit="r/tiktokshop",
        )
    ]

    _, state, reasons, note, _metrics = apply_hotpost_mode_contract(
        mode="rant",
        payload=payload,
        top_posts=posts,
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["sales", "traffic", "conversion"],
        raw_posts=1,
        relevance_filtered=0,
    )

    assert state == "preview"
    assert any(reason.startswith("preview:") for reason in reasons)
    assert "先保留最强信号" in note


def test_apply_hotpost_mode_contract_preview_note_calls_out_retrieval_mismatch() -> None:
    payload = {
        "pain_points": [],
        "top_quotes": [{"quote": "Traffic is there, but no sales are coming through.", "url": "https://reddit.com/x"}],
    }
    posts = [
        _post(
            idx=1,
            title="TikTok Shop has fallen off",
            body="Traffic is still there, but sales have dried up.",
            subreddit="r/tiktokshop",
        )
    ]

    _, state, reasons, note, metrics = apply_hotpost_mode_contract(
        mode="rant",
        payload=payload,
        top_posts=posts,
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["sales", "traffic", "conversion"],
        raw_posts=18,
        relevance_filtered=14,
        relevant_posts=4,
    )

    assert state == "preview"
    assert any(reason.startswith("preview:") for reason in reasons)
    assert "抓到 18 条帖子" in note
    assert "高相关只有 4 条" in note
    assert "命中偏了" in note
    assert metrics["strong_quotes"] == 1
