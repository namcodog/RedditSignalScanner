from __future__ import annotations

from app.schemas.hotpost import Hotpost
from app.services.hotpost.evidence_collection_workflow import (
    HotpostEvidenceCollectionDeps,
    HotpostEvidenceCollectionInput,
    collect_hotpost_evidence,
)
from app.services.hotpost.keywords import load_default_hotpost_keywords
from app.services.infrastructure.reddit_client import RedditPost
from app.services.hotpost.retrieval_precision import score_retrieval_candidate


def _reddit_post(*, post_id: str, title: str, body: str, subreddit: str) -> RedditPost:
    return RedditPost(
        id=post_id,
        title=title,
        selftext=body,
        score=12,
        num_comments=3,
        created_utc=0.0,
        subreddit=subreddit,
        author="user",
        url=f"https://reddit.com/{post_id}",
        permalink=f"/r/{subreddit}/comments/{post_id}",
    )


def _hotpost(post: RedditPost, *, rank: int, signals: dict[str, list[str]]) -> Hotpost:
    return Hotpost(
        rank=rank,
        id=post.id,
        title=post.title,
        body_preview=post.selftext[:100],
        score=post.score,
        num_comments=post.num_comments,
        heat_score=post.score + post.num_comments * 2,
        rant_score=10.0,
        rant_signals=[signal for group in signals.values() for signal in group],
        subreddit=post.subreddit,
        author=post.author,
        reddit_url=post.url,
        created_utc=post.created_utc,
        signals=[signal for group in signals.values() for signal in group],
        signal_score=10.0,
        top_comments=[],
    )


async def _noop_rate_budget(*_args: object, **_kwargs: object) -> None:
    return None


def test_score_retrieval_candidate_blocks_suspicious_exam_help_source() -> None:
    decision = score_retrieval_candidate(
        mode="opportunity",
        query_terms=["shopify", "chargeback", "prevention", "software"],
        subreddit="r/OnlineHESIExam",
        title="How to pass my online exam tomorrow",
        body="WhatsApp us for paid help. 100% success rate.",
        signals=[],
        why_relevant="命中关键词: shopify, software",
    )

    assert decision.source_quality == "suspicious"
    assert decision.blocked is True
    assert "疑似广告" in decision.reason


def test_score_retrieval_candidate_boosts_trusted_shopify_context() -> None:
    trusted = score_retrieval_candidate(
        mode="opportunity",
        query_terms=["shopify", "chargeback", "prevention", "software"],
        subreddit="r/shopify",
        title="Looking for Shopify chargeback prevention software",
        body="Manual review is too slow for disputed orders.",
        signals=["looking for", "workflow"],
    )
    unknown = score_retrieval_candidate(
        mode="opportunity",
        query_terms=["shopify", "chargeback", "prevention", "software"],
        subreddit="r/SaaSDevelopers",
        title="Looking for Shopify chargeback prevention software",
        body="Manual review is too slow for disputed orders.",
        signals=["looking for", "workflow"],
    )

    assert trusted.source_quality == "trusted"
    assert trusted.blocked is False
    assert trusted.score > unknown.score


def test_score_retrieval_candidate_drops_story_context_with_forbidden_terms() -> None:
    decision = score_retrieval_candidate(
        mode="opportunity",
        query_terms=["shopify", "chargeback", "prevention", "software"],
        subreddit="r/startups",
        title="Storytime: our wildest chargeback weekend",
        body="This is mostly a story thread, not a tool search.",
        signals=["chargeback"],
        positive_intent_terms=["software", "prevention"],
        forbidden_context_terms=["storytime"],
        domain_terms=["shopify", "chargeback"],
    )

    assert decision.blocked is False
    assert decision.keep is False
    assert "错误语境" in decision.reason


def test_score_retrieval_candidate_drops_unknown_opportunity_source_without_visible_product_context() -> None:
    decision = score_retrieval_candidate(
        mode="opportunity",
        query_terms=["shopify", "chargeback", "automation", "software"],
        subreddit="r/MerchantProtection",
        title="Cutting chargebacks early: 3 pragmatic moves that actually reduce disputes",
        body="Dispute operations need better triage, but this is not a software buying thread.",
        signals=["same problem"],
        positive_intent_terms=["software", "automation"],
        forbidden_context_terms=["exam", "storytime"],
        domain_terms=["shopify", "chargeback", "dispute"],
    )

    assert decision.keep is False
    assert "产品语境" in decision.reason


def test_score_retrieval_candidate_drops_shopify_post_without_strict_problem_anchor() -> None:
    decision = score_retrieval_candidate(
        mode="opportunity",
        query_terms=["shopify", "chargeback", "response", "automation", "tool"],
        subreddit="r/shopify",
        title="Shopify Comic Retailer Looking for Listing Automation Solutions",
        body="Need listing automation for Shopify and inventory sync.",
        signals=["looking for"],
        positive_intent_terms=["tool", "automation"],
        forbidden_context_terms=["exam", "storytime"],
        domain_terms=["shopify", "chargeback", "response"],
        strict_domain_terms=["chargeback", "response"],
        strict_anchor_min_hits=1,
    )

    assert decision.keep is False
    assert "严格问题域" in decision.reason


def test_score_retrieval_candidate_drops_generic_rant_post_without_problem_anchor() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["tiktok", "seller", "support", "issue"],
        subreddit="r/socialmedia",
        title="Anyone else exhausted by social media lately",
        body="This is a generic vent about content burnout, not a seller support issue.",
        signals=["complaint"],
        positive_intent_terms=["issue", "complaint"],
        forbidden_context_terms=["storytime"],
        domain_terms=["tiktok", "seller", "support"],
        strict_domain_terms=["tiktok", "support"],
        strict_anchor_min_hits=1,
    )

    assert decision.keep is False
    assert "严格问题域" in decision.reason


def test_score_retrieval_candidate_keeps_rant_post_with_sales_alias_anchor() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["tiktok", "traffic", "conversions", "purchases"],
        subreddit="r/tiktokhelp",
        title="Getting views on TikTok but no sales at all",
        body="Traffic is there, but buyers are not converting.",
        signals=["complaint"],
        positive_intent_terms=["issue", "complaint"],
        forbidden_context_terms=["storytime"],
        domain_terms=["sales", "traffic", "conversions", "purchases"],
        strict_domain_terms=["sales", "traffic", "conversions", "purchases"],
        strict_anchor_min_hits=1,
    )

    assert decision.keep is True
    assert "sales" in decision.reason


def test_score_retrieval_candidate_boosts_generic_complaint_family_for_trust_gap() -> None:
    generic = score_retrieval_candidate(
        mode="rant",
        query_terms=["coffee", "machine", "complaints"],
        subreddit="r/espresso",
        title="This coffee machine is a scam and support lied",
        body="Misleading specs and bad reviews everywhere.",
        signals=["complaint"],
        query_family="generic_complaint_discovery",
        primary_friction="trust_gap",
    )
    plain = score_retrieval_candidate(
        mode="rant",
        query_terms=["coffee", "machine", "complaints"],
        subreddit="r/espresso",
        title="This coffee machine is a scam and support lied",
        body="Misleading specs and bad reviews everywhere.",
        signals=["complaint"],
    )

    assert generic.score > plain.score


def test_score_retrieval_candidate_keeps_one_sided_comparison_voice_evidence() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["codex", "claude", "complaints"],
        subreddit="r/claude",
        title="Claude keeps missing my intent",
        body="It feels worse lately and still misses key instructions.",
        signals=["complaint"],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["codex", "claude", "complaints"],
        strict_domain_terms=["codex", "claude", "complaints"],
        strict_anchor_min_hits=1,
        query_family="comparison_complaint_discovery",
        request_query="codex vs claude complaints",
    )

    assert decision.keep is True
    assert "claude" in decision.reason


def test_score_retrieval_candidate_keeps_comparison_preference_without_explicit_complaint_words() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["codex", "claude", "instruction", "following"],
        subreddit="r/codex",
        title="Codex follows the whole brief better than Claude",
        body="It keeps the full brief in mind and understands long instructions much better.",
        signals=[],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["codex", "claude", "instruction"],
        strict_domain_terms=["codex", "claude", "instruction"],
        strict_anchor_min_hits=1,
        query_family="comparison_complaint_discovery",
        request_query="why do people prefer codex over claude for instruction following",
    )

    assert decision.keep is True
    assert "直接命中" in decision.reason


def test_score_retrieval_candidate_keeps_one_sided_compare_post_with_compare_cue() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["codex", "claude", "instruction", "following"],
        subreddit="r/codex",
        title="Codex better than alternatives for long instruction following",
        body="It keeps constraints better than most tools in multi-step coding tasks.",
        signals=[],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["codex", "claude", "instruction"],
        strict_domain_terms=["codex", "claude", "instruction"],
        strict_anchor_min_hits=1,
        query_family="comparison_complaint_discovery",
        request_query="why do developers prefer codex over claude for instruction following",
    )

    assert decision.keep is True


def test_score_retrieval_candidate_drops_compare_post_with_wrong_opponent() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["codex", "claude", "instruction", "following"],
        subreddit="r/codex",
        title="Codex vs Opus inferring instructions",
        body="Codex needs explicit instructions and is worse than Opus at inferring what to do from context.",
        signals=[],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["codex", "claude", "instruction"],
        strict_domain_terms=["codex", "claude", "instruction"],
        strict_anchor_min_hits=1,
        query_family="comparison_complaint_discovery",
        request_query="why do developers prefer codex over claude for instruction following",
    )

    assert decision.keep is False
    assert "错误比较对象" in decision.reason


def test_score_retrieval_candidate_drops_generic_rant_without_pain_anchor_even_if_subject_matches() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["dyson", "complaints"],
        subreddit="r/dyson",
        title="Dyson setup tips for new owners",
        body="Sharing nozzle cleaning routine and filter maintenance checklist.",
        signals=["discussion"],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["dyson", "complaints"],
        strict_domain_terms=["dyson", "complaints"],
        strict_anchor_min_hits=1,
        query_family="generic_complaint_discovery",
        request_query="why do people complain about dyson hair dryer",
    )

    assert decision.keep is False
    assert "抱怨锚点" in decision.reason


def test_score_retrieval_candidate_keeps_specific_issue_with_explicit_voice_failure_signal() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["notion", "ai", "issue"],
        subreddit="r/notion",
        title="Notion AI keeps rewriting my notes into fluff",
        body="The output sounds polished but says nothing useful and keeps ignoring what I wrote.",
        signals=["garbage", "useless"],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["notion", "ai"],
        strict_domain_terms=["notion", "ai"],
        strict_anchor_min_hits=1,
        query_family="specific_issue",
        request_query="why notion ai keeps rewriting my notes into fluff",
    )

    assert decision.keep is True
    assert "notion" in decision.reason


def test_score_retrieval_candidate_keeps_specific_issue_with_subject_and_symptom_anchor_without_generic_complaint_word() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["notion", "ai", "notes", "issue", "weekly", "copy"],
        subreddit="r/notion",
        title="Notion AI turns weekly notes into polished PR copy",
        body="The recap sounds upbeat but omits decisions and action owners.",
        signals=[],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["notion", "ai", "notes"],
        strict_domain_terms=["notion", "ai"],
        strict_anchor_min_hits=1,
        query_family="specific_issue",
        request_query="why notion ai turns weekly notes into polished copy",
    )

    assert decision.keep is True
    assert "症状锚点" in decision.reason


def test_score_retrieval_candidate_keeps_comparison_single_side_signal_with_penalty_instead_of_hard_drop() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["codex", "claude", "instruction", "following"],
        subreddit="r/claude",
        title="Claude needs repeated context for coding briefs",
        body="I restate constraints every turn to keep it aligned.",
        signals=[],
        positive_intent_terms=["issue", "complaint"],
        domain_terms=["codex", "claude", "instruction"],
        strict_domain_terms=["codex", "claude", "instruction"],
        strict_anchor_min_hits=1,
        query_family="comparison_complaint_discovery",
        request_query="why codex vs claude instruction following",
    )

    assert decision.keep is True
    assert "单边命中" in decision.reason


def test_score_retrieval_candidate_penalizes_platform_conversion_help_seekers() -> None:
    direct = score_retrieval_candidate(
        mode="rant",
        query_terms=["tiktok", "ads", "sales", "conversion"],
        subreddit="r/tiktokads",
        title="10 days tiktok ads 0 sales",
        body="Traffic is there but no sales are landing at all.",
        signals=["complaint"],
        query_family="platform_conversion_friction",
        primary_friction="weak_buy_reason",
    )
    helper = score_retrieval_candidate(
        mode="rant",
        query_terms=["tiktok", "ads", "sales", "conversion"],
        subreddit="r/tiktokads",
        title="My ad is crushing but im getting no sales, can someone reach out?",
        body="If somebody can reach out that does tiktok ads with ecommerce i would be very happy.",
        signals=["complaint"],
        query_family="platform_conversion_friction",
        primary_friction="weak_buy_reason",
    )

    assert direct.score > helper.score


def test_score_retrieval_candidate_demotes_post_purchase_noise_for_platform_conversion() -> None:
    pre_purchase = score_retrieval_candidate(
        mode="rant",
        query_terms=["tiktok", "ads", "sales", "conversion"],
        subreddit="r/tiktokads",
        title="TikTok Ads not tracking clicks",
        body="The ads get sessions but the pixel is not tracking conversions at checkout.",
        signals=["complaint"],
        query_family="platform_conversion_friction",
        primary_friction="weak_buy_reason",
    )
    post_purchase = score_retrieval_candidate(
        mode="rant",
        query_terms=["tiktok", "ads", "sales", "conversion"],
        subreddit="r/tiktokshop",
        title="tiktokshop cancelled my order but it still came and it was a scam",
        body="The order was delivered after cancellation and the package felt like a scam.",
        signals=["complaint"],
        query_family="platform_conversion_friction",
        primary_friction="weak_buy_reason",
    )

    assert pre_purchase.score > post_purchase.score


def test_score_retrieval_candidate_drops_platform_conversion_post_without_conversion_anchor() -> None:
    decision = score_retrieval_candidate(
        mode="rant",
        query_terms=["instagram", "reels", "views", "sales"],
        subreddit="r/instagrammarketing",
        title="Instagram support offer is a waste of money",
        body="They gave no useful guidance and the program felt expensive.",
        signals=["complaint"],
        query_family="platform_conversion_friction",
        primary_friction="weak_buy_reason",
    )

    assert decision.keep is False
    assert "转化问题锚点" in decision.reason


async def test_collect_hotpost_evidence_filters_suspicious_sources_for_opportunity() -> None:
    async def _search_posts(
        query: str,
        *,
        limit: int,
        time_filter: str,
        sort: str,
    ) -> list[RedditPost]:
        assert query == "shopify chargeback prevention software"
        return [
            _reddit_post(
                post_id="p-good",
                title="Looking for Shopify chargeback prevention software",
                body="Need a better way to stop fraudulent disputes.",
                subreddit="r/shopify",
            ),
            _reddit_post(
                post_id="p-bad",
                title="Looking for help to take my exam online",
                body="WhatsApp us for paid help and 100% success.",
                subreddit="r/OnlineHESIExam",
            ),
        ]

    async def _fetch_comments(_post_id: str, *, queue_tracker: object | None = None) -> list[dict[str, object]]:
        return []

    result = await collect_hotpost_evidence(
        workflow_input=HotpostEvidenceCollectionInput(
            request_query="shopify chargeback prevention software",
            query_parts=["shopify chargeback prevention software"],
            keywords=["shopify", "chargeback", "prevention", "software"],
            mode="opportunity",
            time_filter="month",
            sort="relevance",
            limit=10,
            requested_subreddits=None,
            suggest_subreddits_when_missing=False,
            enable_relevance_filter=True,
            max_posts_per_subreddit=30,
            max_comment_posts=8,
            notes=[],
        ),
        deps=HotpostEvidenceCollectionDeps(
            acquire_rate_budget=_noop_rate_budget,
            search_subreddits=None,
            search_subreddit_posts=None,
            search_posts=_search_posts,
            fetch_comments=_fetch_comments,
            select_signals=lambda _mode, text: {"need": ["looking for"]} if "looking for" in text.lower() else {"need": []},
            sentiment_label=lambda _mode, _text, _signals: "neutral",
            build_post=_hotpost,
            build_pain_points=lambda _posts, _categories: [],
            confidence_level=lambda evidence_count: "low" if evidence_count < 10 else "medium",
            lexicon=load_default_hotpost_keywords(),
        ),
    )

    assert result.raw_posts == 2
    assert result.filtered_posts == 1
    assert result.relevance_filtered == 1
    assert [post.id for post in result.top_posts] == ["p-good"]
    assert result.top_posts[0].why_important is None


async def test_collect_hotpost_evidence_filters_weak_rant_without_anchor() -> None:
    async def _search_posts(
        query: str,
        *,
        limit: int,
        time_filter: str,
        sort: str,
    ) -> list[RedditPost]:
        assert query == "tiktok seller support issue"
        return [
            _reddit_post(
                post_id="p-good",
                title="TikTok seller support issue is getting worse",
                body="Support keeps closing tickets without solving payout problems.",
                subreddit="r/TikTok",
            ),
            _reddit_post(
                post_id="p-bad",
                title="Anyone else exhausted by social media lately",
                body="This is a generic vent about content burnout, not a seller support issue.",
                subreddit="r/socialmedia",
            ),
        ]

    async def _fetch_comments(_post_id: str, *, queue_tracker: object | None = None) -> list[dict[str, object]]:
        return []

    result = await collect_hotpost_evidence(
        workflow_input=HotpostEvidenceCollectionInput(
            request_query="tiktok seller support issue",
            query_parts=["tiktok seller support issue"],
            keywords=["tiktok", "seller", "support", "issue"],
            mode="rant",
            time_filter="all",
            sort="top",
            limit=10,
            requested_subreddits=None,
            suggest_subreddits_when_missing=False,
            enable_relevance_filter=True,
            max_posts_per_subreddit=30,
            max_comment_posts=8,
            notes=[],
            positive_intent_terms=["issue", "complaint"],
            forbidden_context_terms=["storytime"],
            domain_terms=["tiktok", "seller", "support"],
            strict_domain_terms=["tiktok", "support"],
            strict_anchor_min_hits=1,
        ),
        deps=HotpostEvidenceCollectionDeps(
            acquire_rate_budget=_noop_rate_budget,
            search_subreddits=None,
            search_subreddit_posts=None,
            search_posts=_search_posts,
            fetch_comments=_fetch_comments,
            select_signals=lambda _mode, text: {"strong": ["issue"]} if "issue" in text.lower() else {"strong": ["complaint"]},
            sentiment_label=lambda _mode, _text, _signals: "negative",
            build_post=_hotpost,
            build_pain_points=lambda _posts, _categories: [],
            confidence_level=lambda evidence_count: "low" if evidence_count < 10 else "medium",
            lexicon=load_default_hotpost_keywords(),
        ),
    )

    assert result.raw_posts == 2
    assert result.filtered_posts == 1
    assert result.relevance_filtered == 1
    assert [post.id for post in result.top_posts] == ["p-good"]
