from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.card_lane_policy import infer_validation_lane, resolve_lane


def _candidate(**overrides) -> CandidatePack:
    payload = {
        "candidate_id": "cand-hot-001",
        "signal_id": "sig-hot-001",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 与自动化",
        "topic_pack_id": "upstream-winds",
        "query": "listing:hot:day",
        "matched_subreddit": "artificial",
        "post_id": "abc123",
        "title": "Google pushes AI search harder",
        "score": 680,
        "num_comments": 92,
        "created_at": "2026-04-09T00:00:00Z",
        "collected_at": "2026-04-09T00:00:00Z",
        "collect_batch_id": "batch-1",
        "time_window": "24h",
        "signal_level": "hot",
        "why_now_reason": "new_threads_24h",
        "listing_source": "listing:hot:day",
        "primary_reason": "upstream-winds:listing_hot",
        "matched_keywords": [],
        "top_communities": ["r/artificial"],
        "thread_count": 1,
        "community_count": 1,
        "quote_count": 2,
        "intent_tags": ["趋势变化"],
        "evidence_quotes": [
            {"text": "This changes how people talk about Google AI.", "community": "r/artificial", "permalink": "https://reddit.com/1"},
            {"text": "The scale question matters more than the benchmark.", "community": "r/artificial", "permalink": "https://reddit.com/2"},
        ],
    }
    payload.update(overrides)
    return CandidatePack.model_validate(payload)


def test_seed_validation_draft_marks_listing_hot_candidate_as_hot_lane() -> None:
    draft = seed_validation_draft(
        _candidate(
            title="I have been coding for 11 years and caught myself giving every problem to AI first",
            evidence_quotes=[
                {
                    "text": "I caught myself that my first instinct is to feed the problem to the AI instead of think myself, and it disturbed me a lot.",
                    "community": "r/artificial",
                    "permalink": "https://reddit.com/1",
                },
                {
                    "text": "I don't think AI means less thinking at all for me because I still review every solution and sometimes it helps me realize a better one exists.",
                    "community": "r/artificial",
                    "permalink": "https://reddit.com/2",
                },
            ],
        )
    )
    assert draft.lane == "hot"


def test_seed_validation_draft_uses_hot_detail_contract_for_hot_lane() -> None:
    draft = seed_validation_draft(_candidate())

    assert draft.lane == "hot"
    assert set(draft.detail.model_dump().keys()) == {
        "flashpoint",
        "fight_line",
        "why_test_now",
        "continue_signal",
        "stop_signal",
    }


def test_seed_validation_draft_uses_signal_detail_contract_with_min_test_action() -> None:
    draft = seed_validation_draft(
        _candidate(
            title="Some operators are re-checking product pages before touching recovery flows",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="funnel-conversion",
            matched_subreddit="ecommerce",
            signal_level="rising",
            listing_source="search:relevance:week",
            primary_reason="funnel-conversion:listing_keyword_bridge",
            score=6,
            num_comments=8,
            evidence_quotes=[
                {
                    "text": "The product page is where the unanswered questions pile up.",
                    "community": "r/ecommerce",
                    "permalink": "https://reddit.com/1",
                },
                {
                    "text": "Email only reminds them of the page that already failed to answer the question.",
                    "community": "r/ecommerce",
                    "permalink": "https://reddit.com/2",
                },
            ],
        )
    )

    assert draft.lane == "signal"
    assert set(draft.detail.model_dump().keys()) == {
        "pain_point",
        "target_user_and_scene",
        "why_test_now",
        "min_test_action",
        "continue_signal",
        "stop_signal",
    }


def test_resolve_lane_defaults_old_cards_by_card_type() -> None:
    assert resolve_lane(None, card_type="validate") == "signal"
    assert resolve_lane(None, card_type="write") == "breakdown"


def test_infer_validation_lane_demotes_low_information_listing_heat() -> None:
    candidate = _candidate(
        title="This is how an AI generated cow looked 12 years ago",
        evidence_quotes=[
            {"text": "Now it don't just look 100% real", "community": "r/artificial", "permalink": "https://reddit.com/1"},
            {"text": "Personally I fear them.", "community": "r/artificial", "permalink": "https://reddit.com/2"},
        ],
    )
    assert infer_validation_lane(candidate) == "signal"


def test_infer_validation_lane_demotes_ideological_listing_thread() -> None:
    candidate = _candidate(
        title="The public needs to control AI-run infrastructure",
        evidence_quotes=[
            {"text": "In essence, we need to seize the means of production.", "community": "r/artificial", "permalink": "https://reddit.com/1"},
            {"text": "As if public is qualified for it", "community": "r/artificial", "permalink": "https://reddit.com/2"},
        ],
    )
    assert infer_validation_lane(candidate) == "signal"


def test_infer_validation_lane_demotes_practical_share_threads() -> None:
    candidate = _candidate(
        title="Been doing SEO for a decade, want to learn Claude",
        matched_subreddit="SEO",
        source_scope_id="business-growth-ops",
        source_scope_name="商业增长与运营",
        topic_pack_id="organic-discovery",
        evidence_quotes=[
            {"text": "Sharing some of my usedcases that can save a lot of your time.", "community": "r/SEO", "permalink": "https://reddit.com/1"},
            {"text": "I used Claude with GSC data and sitemap work on 20k+ pages.", "community": "r/SEO", "permalink": "https://reddit.com/2"},
        ],
    )
    assert infer_validation_lane(candidate) == "signal"


def test_infer_validation_lane_allows_high_heat_direct_question_thread_as_hot() -> None:
    candidate = _candidate(
        title="Browserbase vs Browserless.. which one actually held up for production agents?",
        topic_pack_id="agent-builder",
        matched_subreddit="automation",
        listing_source="search:relevance:week",
        score=210,
        num_comments=84,
        intent_tags=["求推荐"],
        evidence_quotes=[
            {
                "text": "People are split because Browserbase is easier to start with, but Browserless keeps winning once the team cares about stability.",
                "community": "r/automation",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "The thread stopped being a tool recommendation thread and turned into an argument about what production-ready even means.",
                "community": "r/automation",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_keeps_collective_reporting_question_threads_hot() -> None:
    candidate = _candidate(
        title="Which coding tool did you actually keep after this pricing move?",
        matched_subreddit="ClaudeCode",
        topic_pack_id="upstream-winds",
        listing_source="search:relevance:week",
        score=108,
        num_comments=44,
        intent_tags=["求推荐"],
        evidence_quotes=[
            {
                "text": "I canceled mine this morning and moved the team back to Cursor after the pricing change landed.",
                "community": "r/ClaudeCode",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "We switched to another tool this week because the new bill made the workflow too expensive.",
                "community": "r/ClaudeCode",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_keeps_platform_watch_threads_hot() -> None:
    candidate = _candidate(
        title="OpenAI rolled out the advisor strategy to the platform today",
        matched_subreddit="OpenAI",
        topic_pack_id="upstream-winds",
        listing_source="search:relevance:week",
        score=84,
        num_comments=33,
        intent_tags=["趋势变化"],
        evidence_quotes=[
            {
                "text": "Rolled out today. I'm waiting to see whether the rate limits and quota behavior hold.",
                "community": "r/OpenAI",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "Now available for everyone here, but people are still testing whether it really changes their workflow.",
                "community": "r/OpenAI",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_keeps_collective_reporting_threads_hot() -> None:
    candidate = _candidate(
        title="How are you getting through this economic downturn",
        matched_subreddit="ecommerce",
        source_scope_id="ecommerce-sellers",
        source_scope_name="电商与卖家",
        topic_pack_id="category-winds",
        evidence_quotes=[
            {"text": "After 8 years of solid great work I'm cooked.", "community": "r/ecommerce", "permalink": "https://reddit.com/1"},
            {"text": "I am at 40% lower than Q1 2025 and will revisit my ad spend.", "community": "r/ecommerce", "permalink": "https://reddit.com/2"},
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_keeps_practical_direct_question_threads_signal() -> None:
    candidate = _candidate(
        title="Which AI note taker should I try first for my solo workflow?",
        matched_subreddit="ChatGPT",
        topic_pack_id="tools-efficiency",
        listing_source="search:relevance:week",
        score=88,
        num_comments=31,
        intent_tags=["求推荐"],
        evidence_quotes=[
            {
                "text": "I only need a simple setup for my own calls and want the least annoying onboarding.",
                "community": "r/ChatGPT",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "Mostly looking for a practical recommendation before I pay for anything.",
                "community": "r/ChatGPT",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "signal"


def test_infer_validation_lane_demotes_blocked_hot_subreddits() -> None:
    candidate = _candidate(
        matched_subreddit="CleaningTips",
        source_scope_id="ecommerce-sellers",
        source_scope_name="电商与卖家",
        topic_pack_id="category-winds",
        title='UPDATE: I told depression "No More"',
        evidence_quotes=[
            {"text": "My current progress is finally visible and I feel better.", "community": "r/CleaningTips", "permalink": "https://reddit.com/1"},
            {"text": "This is the push I needed today.", "community": "r/CleaningTips", "permalink": "https://reddit.com/2"},
        ],
    )
    assert infer_validation_lane(candidate) == "signal"


def test_infer_validation_lane_demotes_listing_from_search_only_pack() -> None:
    candidate = _candidate(
        topic_pack_id="tools-efficiency",
        matched_subreddit="ChatGPT",
        title="Which AI subscription did you keep?",
        evidence_quotes=[
            {"text": "I kept Claude and canceled the rest.", "community": "r/ChatGPT", "permalink": "https://reddit.com/1"},
            {"text": "I moved to one tool because context switching was killing me.", "community": "r/ChatGPT", "permalink": "https://reddit.com/2"},
        ],
    )
    assert infer_validation_lane(candidate) == "signal"


def test_infer_validation_lane_keeps_statement_style_listing_debate_hot() -> None:
    candidate = _candidate(
        title="Monetization truly doesn’t care how big your user base is",
        matched_subreddit="OpenAI",
        intent_tags=["求推荐"],
        evidence_quotes=[
            {
                "text": "Anthropic counts revenue very differently than OpenAI and that changes how the comparison looks.",
                "community": "r/OpenAI",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "They do not overtake OpenAI. They just calculate revenue in a different way.",
                "community": "r/OpenAI",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_keeps_collective_short_reactions_hot() -> None:
    candidate = _candidate(
        title="SEMRush charged me $211 using deceptive dark patterns to prevent trial cancellation",
        matched_subreddit="SEO",
        source_scope_id="business-growth-ops",
        source_scope_name="商业增长与运营",
        topic_pack_id="organic-discovery",
        signal_level="rising",
        score=129,
        num_comments=67,
        intent_tags=["趋势变化"],
        evidence_quotes=[
            {
                "text": "No, but a chargeback is the solution. Obviously scammy tactics to prevent cancellations.",
                "community": "r/SEO",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "Classic SEMrush. Predatory company.",
                "community": "r/SEO",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_allows_search_based_hot_when_discussion_shape_is_strong() -> None:
    candidate = _candidate(
        listing_source="search:relevance:week",
        topic_pack_id="agent-builder",
        matched_subreddit="OpenAI",
        title="Open source routes are exposing how thin most agent demos really are",
        score=420,
        num_comments=91,
        signal_level="hot",
        intent_tags=["趋势变化"],
        evidence_quotes=[
            {
                "text": "The argument is no longer whether agents can code, but whether any of these stacks survive real business constraints.",
                "community": "r/OpenAI",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "People are split between open source routes and API-first products because they optimize for completely different failure modes.",
                "community": "r/OpenAI",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_keeps_high_heat_sustained_megathread_hot() -> None:
    candidate = _candidate(
        title="The era of human coding is over",
        matched_subreddit="singularity",
        signal_level="sustained",
        score=3000,
        num_comments=720,
        intent_tags=["趋势变化"],
        evidence_quotes=[
            {
                "text": "I do not think people understand how quickly this changes expectations for software teams.",
                "community": "r/singularity",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "Everyone in this thread is arguing about whether this is real leverage or just hype with better demos.",
                "community": "r/singularity",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_keeps_title_driven_sustained_hot() -> None:
    candidate = _candidate(
        title="The era of human coding is over",
        matched_subreddit="singularity",
        signal_level="sustained",
        score=3010,
        num_comments=720,
        intent_tags=["趋势变化"],
        evidence_quotes=[
            {
                "text": "This forces every team to rethink what coding leverage even means.",
                "community": "r/singularity",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "Some people think this is hype, others think the workflow already changed.",
                "community": "r/singularity",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_allows_search_hot_when_discussion_is_real() -> None:
    candidate = _candidate(
        source_scope_id="business-growth-ops",
        source_scope_name="商业增长与运营",
        topic_pack_id="organic-discovery",
        matched_subreddit="DigitalMarketing",
        listing_source="search:relevance:week",
        signal_level="hot",
        score=155,
        num_comments=68,
        title="SEO Was Not Enough. Now We Have GEO",
        intent_tags=["趋势变化"],
        evidence_quotes=[
            {
                "text": "Everyone in this thread is now debating whether GEO is replacing old SEO playbooks or just renaming them.",
                "community": "r/DigitalMarketing",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "I don't think this is just a naming change because the traffic mix and citation logic already shifted.",
                "community": "r/DigitalMarketing",
                "permalink": "https://reddit.com/2",
            },
        ],
    )
    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_demotes_search_hot_for_practical_recommendation_threads() -> None:
    candidate = _candidate(
        source_scope_id="ecommerce-sellers",
        source_scope_name="电商与卖家",
        topic_pack_id="selection-signals",
        title="This is my knife. Why is your knife better?",
        matched_subreddit="knives",
        listing_source="search:relevance:week",
        score=149,
        num_comments=199,
        signal_level="rising",
        evidence_quotes=[
            {
                "text": "Mine keeps slipping in hand.",
                "community": "r/knives",
                "permalink": "https://reddit.com/1",
            },
            {
                "text": "I switched because the steel holds up better.",
                "community": "r/knives",
                "permalink": "https://reddit.com/2",
            },
        ],
        intent_tags=["求推荐"],
    )

    assert infer_validation_lane(candidate) == "signal"


def test_infer_validation_lane_allows_title_driven_hot_without_quotes() -> None:
    candidate = _candidate(
        source_scope_id="business-growth-ops",
        source_scope_name="商业增长与运营",
        topic_pack_id="organic-discovery",
        matched_subreddit="FacebookAds",
        listing_source="listing:rising:day",
        signal_level="rising",
        score=18,
        num_comments=28,
        title="Meta ads are cooked now. It's not a question anymore",
        evidence_quotes=[],
    )

    assert infer_validation_lane(candidate) == "hot"


def test_infer_validation_lane_allows_title_driven_sustained_hot_without_quotes() -> None:
    candidate = _candidate(
        source_scope_id="business-growth-ops",
        source_scope_name="商业增长与运营",
        topic_pack_id="organic-discovery",
        matched_subreddit="SEO",
        listing_source="listing:hot:day",
        signal_level="sustained",
        score=34,
        num_comments=26,
        title="Anthropic Leak: Internal Claude Codebase and Agent Tools Exposed",
        evidence_quotes=[],
    )

    assert infer_validation_lane(candidate) == "hot"
