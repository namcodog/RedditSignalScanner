from __future__ import annotations

from app.services.hotpost.signal_input_quality import assess_signal_input_quality


def test_quality_gate_blocks_single_thread_with_only_low_value_quote() -> None:
    result = assess_signal_input_quality(
        {
            "thread_count": 1,
            "community_count": 1,
            "evidence_quotes": [{"text": "Hi, hit me up if you ever want to chat"}],
        }
    )
    assert result["should_block"] is True
    assert "no_substantive_quotes" in result["reasons"]


def test_quality_gate_allows_multi_quote_signal_with_real_content() -> None:
    result = assess_signal_input_quality(
        {
            "thread_count": 2,
            "community_count": 1,
            "evidence_quotes": [
                {"text": "The worst part is it silently fixes malformed JSON instead of surfacing the upstream error."},
                {"text": "The pipeline looks green, but the data already drifted away from the original intent."},
            ],
        }
    )
    assert result["should_block"] is False
    assert result["substantive_quote_count"] == 2


def test_quality_gate_keeps_short_but_sharp_chinese_quote() -> None:
    result = assess_signal_input_quality(
        {
            "thread_count": 2,
            "community_count": 1,
            "evidence_quotes": [
                {"text": "它不是帮我提炼，而是把我的笔记磨成一层空壳。"},
                {"text": "最烦的是听起来更顺，但信息密度直接掉下去了。"},
            ],
        }
    )
    assert result["should_block"] is False


def test_quality_gate_blocks_single_thread_complaint_only_signal() -> None:
    result = assess_signal_input_quality(
        {
            "thread_count": 1,
            "community_count": 1,
            "intent_tags": ["明确阻塞 / 吐槽到影响行动"],
            "evidence_quotes": [
                {"text": "Reddit Ads is the worst money I have spent this year."},
                {"text": "It feels like junk traffic and I am done with it."},
            ],
        }
    )
    assert result["should_block"] is True
    assert "complaint_only_no_market_signal" in result["reasons"]


def test_quality_gate_blocks_meta_community_complaint_signal() -> None:
    result = assess_signal_input_quality(
        {
            "title": "Can we stop with clickbaity titles",
            "thread_count": 1,
            "community_count": 1,
            "intent_tags": ["避坑"],
            "evidence_quotes": [
                {"text": "Can we stop with the click baity 'and this is what I found' titles. It's getting old."},
                {"text": "People are shitting on you about the headline."},
            ],
        }
    )
    assert result["should_block"] is True
    assert "meta_community_complaint" in result["reasons"]


def test_quality_gate_allows_product_page_title_feedback() -> None:
    result = assess_signal_input_quality(
        {
            "title": "New to sub, looking to learn",
            "thread_count": 1,
            "community_count": 1,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {
                    "text": "The listing doesn’t explain the product. I still don’t clearly know what it is or why I need it. Your title is too vague to carry the sale."
                },
                {
                    "text": "$35k revenue with 50% profit is a strong place to be. Now it is more about tightening the listing so more traffic converts."
                },
            ],
        }
    )
    assert "meta_community_complaint" not in result["reasons"]


def test_quality_gate_allows_seo_basics_discussion() -> None:
    result = assess_signal_input_quality(
        {
            "title": "How are you guys building your websites and handling SEO?",
            "thread_count": 1,
            "community_count": 1,
            "intent_tags": ["求推荐"],
            "evidence_quotes": [
                {
                    "text": "A clean fast site matters more than doing something overly clever. I would fix checkout friction before chasing advanced SEO."
                },
                {
                    "text": "Focus on solid H1s and Meta Titles, strong category pages, and clear trust signals before anything fancy."
                },
            ],
        }
    )
    assert "meta_community_complaint" not in result["reasons"]


def test_quality_gate_blocks_joke_article_signal() -> None:
    result = assess_signal_input_quality(
        {
            "title": "Fisher-Price Is Pivoting to AI-Powered Autonomous Weapons Manufacturing",
            "thread_count": 1,
            "community_count": 1,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {"text": "This is a joke article btw"},
                {"text": "Next thing you tell me is LEGO is making grenades."},
            ],
        }
    )
    assert result["should_block"] is True
    assert "joke_or_satire_low_signal" in result["reasons"]
