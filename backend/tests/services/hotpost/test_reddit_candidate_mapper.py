from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.hotpost_source_scopes import RedditSearchSpec
from app.services.hotpost.reddit_candidate_mapper import build_candidate_pack


class _Post:
    def __init__(
        self,
        *,
        title: str,
        selftext: str,
        subreddit: str = "SEO",
        score: int = 42,
        comments: int = 12,
        created_utc: float | None = None,
    ) -> None:
        self.id = "post-1"
        self.subreddit = subreddit
        self.title = title
        self.selftext = selftext
        self.score = score
        self.num_comments = comments
        self.created_utc = created_utc or (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
        self.permalink = f"/r/{subreddit}/comments/post-1/test"


def _listing_spec(pack: str, subreddit: str = "SEO") -> RedditSearchSpec:
    return RedditSearchSpec(
        source_scope_id="business-growth-ops",
        topic_pack_id=pack,
        subreddit=subreddit,
        mode="listing",
        sort="hot",
        time_filter="day",
        listing_source="listing:hot:day",
        primary_reason=f"{pack}:listing_keyword_bridge",
    )


def test_organic_listing_bridge_rejects_generic_seo_tool_threads() -> None:
    spec = _listing_spec("organic-discovery", "SEO")
    post = _Post(
        title="Weekly SEO megathread: best tools this week",
        selftext="Is Ahrefs or Semrush better for GEO and SEO work?",
        score=150,
        comments=30,
    )

    candidate = build_candidate_pack(spec, post, [], collect_batch_id="batch-1", collected_at=post_time())

    assert candidate is None


def test_organic_listing_bridge_keeps_traffic_quality_change_threads() -> None:
    spec = _listing_spec("organic-discovery", "Emailmarketing")
    post = _Post(
        title="Newsletter traffic is up but buyer quality dropped hard",
        selftext="Our newsletter traffic doubled, but the leads are lower intent and convert worse than before.",
        subreddit="Emailmarketing",
        score=44,
        comments=11,
    )

    candidate = build_candidate_pack(spec, post, [], collect_batch_id="batch-1", collected_at=post_time())

    assert candidate is not None
    assert candidate.topic_pack_id == "organic-discovery"
    assert candidate.primary_reason == "organic-discovery:listing_keyword_bridge"
    assert candidate.signal_level == "rising"
    assert "newsletter traffic" in candidate.matched_keywords


def test_funnel_listing_bridge_requires_concrete_event_leak() -> None:
    spec = _listing_spec("funnel-conversion", "shopify")
    post = _Post(
        title="Why does my checkout drop when shipping cost appears?",
        selftext="Clicks stay steady, but buyers disappear when shipping cost shows up and checkout completion drops.",
        subreddit="shopify",
        score=38,
        comments=14,
    )

    candidate = build_candidate_pack(spec, post, [], collect_batch_id="batch-1", collected_at=post_time())

    assert candidate is not None
    assert candidate.topic_pack_id == "funnel-conversion"
    assert candidate.primary_reason == "funnel-conversion:listing_keyword_bridge"
    assert candidate.signal_level == "rising"
    assert "checkout" in candidate.matched_keywords


def test_funnel_listing_bridge_rejects_generic_cro_advice() -> None:
    spec = _listing_spec("funnel-conversion", "CRO")
    post = _Post(
        title="What is a good conversion rate for ecommerce?",
        selftext="Need generic CRO tips and best practices for a better landing page.",
        subreddit="CRO",
        score=90,
        comments=25,
    )

    candidate = build_candidate_pack(spec, post, [], collect_batch_id="batch-1", collected_at=post_time())

    assert candidate is None


def test_funnel_listing_bridge_keeps_payment_processor_replacement_threads() -> None:
    spec = _listing_spec("funnel-conversion", "shopify")
    post = _Post(
        title="Need a New Payment Processor",
        selftext="Our current provider keeps holding funds, so we need a new payment processor for the store.",
        subreddit="shopify",
        score=10,
        comments=35,
    )

    candidate = build_candidate_pack(spec, post, [], collect_batch_id="batch-1", collected_at=post_time())

    assert candidate is not None
    assert candidate.topic_pack_id == "funnel-conversion"
    assert candidate.primary_reason == "funnel-conversion:listing_keyword_bridge"
    assert candidate.signal_level == "hot"
    assert "payment processor" in candidate.matched_keywords


def test_funnel_listing_bridge_keeps_shopify_payments_freeze_threads() -> None:
    spec = _listing_spec("funnel-conversion", "shopify")
    post = _Post(
        title="Shopify Payments froze $4,200 and support won't tell me why",
        selftext="Our payouts are under review and the account is frozen.",
        subreddit="shopify",
        score=26,
        comments=53,
    )

    candidate = build_candidate_pack(spec, post, [], collect_batch_id="batch-1", collected_at=post_time())

    assert candidate is not None
    assert candidate.topic_pack_id == "funnel-conversion"
    assert candidate.primary_reason == "funnel-conversion:listing_keyword_bridge"
    assert candidate.signal_level == "hot"
    assert "shopify payments" in candidate.matched_keywords


def post_time():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
