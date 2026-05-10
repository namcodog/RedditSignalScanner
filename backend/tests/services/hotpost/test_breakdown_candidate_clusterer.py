from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.breakdown_candidate_clusterer import list_breakdown_suggestions


def _candidate(
    candidate_id: str,
    *,
    source_scope_id: str,
    topic_pack_id: str,
    post_id: str,
    matched_subreddit: str,
    keyword: str | None,
    quote: str,
    extra_quotes: list[str] | None = None,
    title: str | None = None,
    query: str | None = None,
) -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": source_scope_id,
            "source_scope_name": "测试范围",
            "topic_pack_id": topic_pack_id,
            "query": query or keyword or "listing:hot:day",
            "matched_subreddit": matched_subreddit,
            "post_id": post_id,
            "title": title or f"title-{candidate_id}",
            "score": 10,
            "num_comments": 5,
            "created_at": "2026-04-07T00:00:00Z",
            "collected_at": "2026-04-07T00:10:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_hot",
            "primary_reason": "test",
            "matched_keywords": [keyword] if keyword else [],
            "top_communities": [f"r/{matched_subreddit}"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["求推荐"],
            "evidence_quotes": [
                {
                    "text": text,
                    "community": f"r/{matched_subreddit}",
                    "permalink": f"https://reddit.com/{post_id}",
                }
                for text in [quote, *(extra_quotes or [])]
            ],
        }
    )


def test_breakdown_suggestions_only_allow_v1_whitelist(monkeypatch) -> None:
    from app.services.hotpost import breakdown_candidate_clusterer as mod

    monkeypatch.setattr(
        mod,
        "list_candidates",
        lambda source_scope_id=None: [
            _candidate(
                "cand-1",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p1",
                matched_subreddit="OpenAI",
                keyword="agent audit",
                quote="Agents need audit trails before enterprises trust them.",
            ),
            _candidate(
                "cand-2",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p2",
                matched_subreddit="artificial",
                keyword="agent audit",
                quote="Without an audit trail, teams will not roll agents out.",
            ),
            _candidate(
                "cand-2b",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p2b",
                matched_subreddit="OpenAI",
                keyword="agent audit",
                quote="Teams need clear audit logs before they trust agents in production.",
            ),
            _candidate(
                "cand-3",
                source_scope_id="ai-automation",
                topic_pack_id="tools-efficiency",
                post_id="p3",
                matched_subreddit="ChatGPT",
                keyword="workflow template",
                quote="This template saves me hours every week.",
            ),
            _candidate(
                "cand-4",
                source_scope_id="ai-automation",
                topic_pack_id="tools-efficiency",
                post_id="p4",
                matched_subreddit="ChatGPTPro",
                keyword="workflow template",
                quote="Our team reuses the same workflow prompts all day.",
            ),
        ],
    )

    items = list_breakdown_suggestions()

    assert len(items) == 1
    assert items[0].topic_pack_id == "agent-builder"


def test_breakdown_suggestions_hypothesis_stays_human_readable(monkeypatch) -> None:
    from app.services.hotpost import breakdown_candidate_clusterer as mod

    monkeypatch.setattr(
        mod,
        "list_candidates",
        lambda source_scope_id=None: [
            _candidate(
                "cand-5",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals",
                post_id="p5",
                matched_subreddit="BuyItForLife",
                keyword="spout material durability",
                quote="I keep replacing drink dispensers because the spout cracks first.",
            ),
            _candidate(
                "cand-6",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals",
                post_id="p6",
                matched_subreddit="Coffee",
                keyword="spout material durability",
                quote="People no longer trust pretty glass if the weak point is obvious and the spout fails fast.",
            ),
            _candidate(
                "cand-7",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals",
                post_id="p7",
                matched_subreddit="BuyItForLife",
                keyword="spout material durability",
                quote="Once the spout fails, buyers start asking what material actually lasts.",
            ),
        ],
    )

    items = list_breakdown_suggestions()

    assert len(items) == 1
    assert "selection-signals" not in items[0].hypothesis
    assert "购买标准" in items[0].hypothesis


def test_breakdown_suggestions_skip_groups_below_breakdown_bar(monkeypatch) -> None:
    from app.services.hotpost import breakdown_candidate_clusterer as mod

    monkeypatch.setattr(
        mod,
        "list_candidates",
        lambda source_scope_id=None: [
            _candidate(
                "cand-8",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals",
                post_id="p8",
                matched_subreddit="BuyItForLife",
                keyword="repairable lamp",
                quote="If this lamp had replaceable parts, I would keep it forever.",
            ),
            _candidate(
                "cand-9",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals",
                post_id="p9",
                matched_subreddit="Coffee",
                keyword="repairable lamp",
                quote="I would buy it again if the battery were easier to replace.",
            ),
        ],
    )

    assert list_breakdown_suggestions() == []


def test_breakdown_suggestions_allow_organic_discovery(monkeypatch) -> None:
    from app.services.hotpost import breakdown_candidate_clusterer as mod

    monkeypatch.setattr(
        mod,
        "list_candidates",
        lambda source_scope_id=None: [
            _candidate(
                "cand-10",
                source_scope_id="business-growth-ops",
                topic_pack_id="organic-discovery",
                post_id="p10",
                matched_subreddit="SEO",
                keyword="geo visibility shift",
                quote="We are seeing GEO visibility shift while classic search traffic gets weaker.",
            ),
            _candidate(
                "cand-11",
                source_scope_id="business-growth-ops",
                topic_pack_id="organic-discovery",
                post_id="p11",
                matched_subreddit="bigseo",
                keyword="geo visibility shift",
                quote="The debate is no longer whether GEO matters, it is whether this visibility shift breaks classic SEO discovery.",
            ),
            _candidate(
                "cand-12",
                source_scope_id="business-growth-ops",
                topic_pack_id="organic-discovery",
                post_id="p12",
                matched_subreddit="DigitalMarketing",
                keyword="geo visibility shift",
                quote="Teams are changing content plans because the same GEO visibility shift is absorbing the first click.",
            ),
        ],
    )

    items = list_breakdown_suggestions()
    assert len(items) == 1
    assert items[0].topic_pack_id == "organic-discovery"


def test_breakdown_suggestions_allow_paid_economics_pair_by_shared_anchor(monkeypatch) -> None:
    from app.services.hotpost import breakdown_candidate_clusterer as mod

    monkeypatch.setattr(
        mod,
        "list_candidates",
        lambda source_scope_id=None: [
            _candidate(
                "cand-13",
                source_scope_id="business-growth-ops",
                topic_pack_id="paid-economics",
                post_id="p13",
                matched_subreddit="Google_Ads",
                keyword=None,
                query="listing:hot:day",
                title="Google ads beginner",
                quote="Google ads is still where beginners burn budget before they learn what converts.",
                extra_quotes=["Beginners on Google ads usually waste money before they understand where the leak starts."],
            ),
            _candidate(
                "cand-14",
                source_scope_id="business-growth-ops",
                topic_pack_id="paid-economics",
                post_id="p14",
                matched_subreddit="PPC",
                keyword=None,
                query="listing:hot:day",
                title="Short term promotion set up on Google Ads",
                quote="Short term promotions on Google Ads still collapse if you do not know where the budget leaks first.",
                extra_quotes=["Teams keep saying Google ads promos fail when the budget leak is never fixed first."],
            ),
        ],
    )

    items = list_breakdown_suggestions()
    assert len(items) == 1
    assert items[0].topic_pack_id == "paid-economics"
    assert set(items[0].candidate_ids) == {"cand-13", "cand-14"}
    assert "google ads" in items[0].hypothesis.lower()


def test_breakdown_suggestions_group_listing_candidates_by_title_anchor(monkeypatch) -> None:
    from app.services.hotpost import breakdown_candidate_clusterer as mod

    monkeypatch.setattr(
        mod,
        "list_candidates",
        lambda source_scope_id=None: [
            _candidate(
                "cand-20",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p20",
                matched_subreddit="OpenAI",
                keyword=None,
                query="listing:hot:day",
                title="Claude Code is becoming the lock-in layer for agent teams",
                quote="Claude Code keeps becoming the workflow lock-in point for more teams.",
            ),
            _candidate(
                "cand-21",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p21",
                matched_subreddit="singularity",
                keyword=None,
                query="listing:hot:day",
                title="Teams are quietly rebuilding around Claude Code lock-in",
                quote="The thread is really about Claude Code turning into a lock-in layer.",
            ),
            _candidate(
                "cand-22",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p22",
                matched_subreddit="ClaudeAI",
                keyword=None,
                query="listing:hot:day",
                title="Claude Code hype is now changing how shops plan dev work",
                quote="Claude Code is now the anchor term in how teams describe their agent workflow.",
            ),
            _candidate(
                "cand-23",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p23",
                matched_subreddit="OpenAI",
                keyword=None,
                query="listing:hot:day",
                title="Browserless reliability issues are annoying again",
                quote="Browserless reliability keeps annoying people in production.",
            ),
            _candidate(
                "cand-24",
                source_scope_id="ai-automation",
                topic_pack_id="agent-builder",
                post_id="p24",
                matched_subreddit="automation",
                keyword=None,
                query="listing:hot:day",
                title="People are debating browser session replay pricing",
                quote="Session replay pricing is the new pain point in this stack.",
            ),
        ],
    )

    items = list_breakdown_suggestions()

    assert len(items) == 1
    assert items[0].topic_pack_id == "agent-builder"
    assert set(items[0].candidate_ids) == {"cand-20", "cand-21", "cand-22"}
