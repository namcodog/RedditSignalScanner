from __future__ import annotations

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.evidence_package import build_hotpost_evidence_package
from app.services.hotpost.hotpost_config import (
    HotpostEvidencePackagingConfig,
    HotpostEvidencePackagingModeConfig,
)


def _build_post(
    *,
    post_id: str,
    title: str,
    body_preview: str,
    why_relevant: str | None = None,
    top_comments: list[HotpostComment] | None = None,
    subreddit: str = "r/shopify",
    signal_score: float = 10.0,
) -> Hotpost:
    return Hotpost(
        rank=1,
        id=post_id,
        title=title,
        body_preview=body_preview,
        score=42,
        num_comments=12,
        heat_score=55,
        rant_score=0.0,
        rant_signals=[],
        subreddit=subreddit,
        author="user",
        reddit_url=f"https://reddit.com/{post_id}",
        created_utc=0.0,
        signals=["automation"],
        signal_score=signal_score,
        why_relevant=why_relevant,
        top_comments=top_comments or [],
    )


def _build_comment(*, body: str, permalink: str, score: int = 10, author: str = "user") -> HotpostComment:
    return HotpostComment(
        comment_fullname=f"t1_{permalink.rsplit('/', 1)[-1]}",
        author=author,
        body=body,
        score=score,
        permalink=permalink,
    )


def _packaging_config() -> HotpostEvidencePackagingConfig:
    return HotpostEvidencePackagingConfig(
        title_max_chars=140,
        why_relevant_max_chars=120,
        focus_terms_limit=4,
        mode_rules={
            "opportunity": HotpostEvidencePackagingModeConfig(
                query_weight=3.0,
                intent_weight=2.0,
                domain_weight=4.0,
                why_relevant_weight=1.0,
                keep_focus_only=True,
                min_post_score=6.0,
                min_comment_score=4.0,
            ),
            "rant": HotpostEvidencePackagingModeConfig(
                query_weight=4.0,
                intent_weight=1.0,
                domain_weight=2.0,
                why_relevant_weight=1.0,
                keep_focus_only=False,
                min_post_score=0.0,
                min_comment_score=0.0,
            ),
        },
    )


def test_build_hotpost_evidence_package_prioritizes_domain_anchored_opportunity_posts() -> None:
    package = build_hotpost_evidence_package(
        mode="opportunity",
        query="shopify automation tool",
        posts=[
            _build_post(
                post_id="p-generic",
                title="Best Shopify automation stack for weekly email updates",
                body_preview="We use a few apps to automate follow-up messages and newsletter flows.",
                why_relevant="命中关键词: shopify, automation, tool",
            ),
            _build_post(
                post_id="p-relevant",
                title="Built a Shopify chargeback evidence automation tool for merchants",
                body_preview="The workflow collects dispute evidence and drafts chargeback response packets.",
                why_relevant="直接命中: chargeback, evidence；意图命中: tool；领域命中: chargeback, evidence",
            ),
        ],
        comments=[
            _build_comment(
                body="We need chargeback evidence automation because manual dispute packets take hours.",
                permalink="/r/shopify/comments/p-relevant/_/real",
                score=22,
            ),
            _build_comment(
                body="same here",
                permalink="/r/shopify/comments/p-generic/_/short",
                score=30,
            ),
        ],
        positive_intent_terms=["automation", "tool"],
        domain_terms=["chargeback", "evidence", "dispute"],
        packaging_config=_packaging_config(),
        getenv=lambda _key, default="": default,
    )

    assert [item["id"] for item in package.posts_data] == ["p-relevant"]
    assert package.posts_data[0]["focus_terms"] == ["shopify", "automation", "tool", "chargeback"]
    assert [item["permalink"] for item in package.comments_data] == [
        "/r/shopify/comments/p-relevant/_/real"
    ]


def test_build_hotpost_evidence_package_keeps_rant_posts_but_ranks_focus_first() -> None:
    package = build_hotpost_evidence_package(
        mode="rant",
        query="shopify chargeback complaints",
        posts=[
            _build_post(
                post_id="p-generic",
                title="Shopify support feels slow again",
                body_preview="General support complaints keep piling up.",
                why_relevant="用户抱怨客服慢",
            ),
            _build_post(
                post_id="p-focus",
                title="Chargeback complaints keep crushing our Shopify margins",
                body_preview="We keep losing chargeback disputes even after uploading delivery proof.",
                why_relevant="直接命中: chargeback；领域命中: chargeback, dispute",
            ),
        ],
        comments=[],
        positive_intent_terms=["complaint"],
        domain_terms=["chargeback", "dispute"],
        packaging_config=_packaging_config(),
        getenv=lambda _key, default="": default,
    )

    assert [item["id"] for item in package.posts_data] == ["p-focus", "p-generic"]
    assert "chargeback" in package.posts_data[0]["focus_terms"]
