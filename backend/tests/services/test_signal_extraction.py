from __future__ import annotations

from typing import List

import pytest

from app.services.analysis.signal_extraction import SignalExtractor


@pytest.fixture
def extractor() -> SignalExtractor:
    return SignalExtractor()


@pytest.fixture
def sample_posts() -> List[dict]:
    return [
        {
            "id": "p1",
            "title": "I hate how slow the onboarding feels for growth teams",
            "summary": "It's confusing to set up and the flow is painfully complex even after multiple attempts.",
            "score": 180,
            "num_comments": 24,
        },
        {
            "id": "p2",
            "title": "Looking for an automation tool that would pay for itself",
            "summary": "Our team would love a solution that sends weekly insight digests automatically.",
            "score": 95,
            "num_comments": 8,
        },
        {
            "id": "p3",
            "title": "Notion vs Evernote showdown",
            "summary": "Which tool offers better integrations for research automation? Curious about competitors to Notion.",
            "score": 140,
            "num_comments": 15,
        },
        {
            "id": "p4",
            "title": "Users can't stand broken export features",
            "summary": "Export is confusing and unreliable, seriously need a better experience here.",
            "score": 60,
            "num_comments": 12,
        },
        {
            "id": "p5",
            "title": "Need a simple way to keep leadership updated",
            "summary": "Looking for a status report automation that does not require manual spreadsheets.",
            "score": 70,
            "num_comments": 6,
        },
    ]


def test_extract_pain_points_ranked_highest_first(extractor: SignalExtractor, sample_posts: List[dict]) -> None:
    signals = extractor.extract(sample_posts, keywords=["onboarding", "automation", "export"])
    assert len(signals.pain_points) >= 2

    top = signals.pain_points[0]
    assert "slow" in top.description.lower() or "confusing" in top.description.lower()
    assert top.frequency >= 1
    assert top.sentiment <= -0.3
    assert "p1" in top.source_posts
    assert top.relevance >= signals.pain_points[-1].relevance


def test_extract_competitors_detects_capitalised_names(extractor: SignalExtractor, sample_posts: List[dict]) -> None:
    signals = extractor.extract(sample_posts, keywords=["automation"])
    competitor_names = [signal.name for signal in signals.competitors]
    assert "Notion" in competitor_names
    notion_signal = next(signal for signal in signals.competitors if signal.name == "Notion")
    assert notion_signal.mention_count >= 1
    assert notion_signal.relevance > 0
    assert any("Notion" in ctx for ctx in notion_signal.context_snippets)
    assert "p3" in notion_signal.source_posts


def test_extract_opportunities_scores_demand_and_urgency(extractor: SignalExtractor, sample_posts: List[dict]) -> None:
    signals = extractor.extract(sample_posts, keywords=["automation"])
    assert len(signals.opportunities) >= 1
    top = signals.opportunities[0]
    assert "looking for" in top.description.lower() or "need" in top.description.lower()
    assert top.demand_score > 0
    assert top.potential_users > 80
    assert "p2" in top.source_posts or "p5" in top.source_posts


def test_extract_pain_points_captures_why_is_pattern(extractor: SignalExtractor) -> None:
    posts = [
        {
            "id": "q1",
            "title": "Why is onboarding so slow for research ops?",
            "summary": "Can't find a reliable workflow that is not painfully slow.",
            "score": 120,
            "num_comments": 12,
        }
    ]

    signals = extractor.extract(posts, keywords=["onboarding"])
    descriptions = [signal.description.lower() for signal in signals.pain_points]
    assert any("why is onboarding so slow" in description for description in descriptions)


def test_extract_pain_points_handles_cant_believe_pattern(extractor: SignalExtractor) -> None:
    posts = [
        {
            "id": "q2",
            "title": "Can't believe exporting is still broken",
            "summary": "It doesn't work for enterprise teams and it's unbelievably frustrating.",
            "score": 110,
            "num_comments": 9,
        }
    ]

    signals = extractor.extract(posts, keywords=["export"])
    descriptions = [signal.description.lower() for signal in signals.pain_points]
    assert any("can't believe" in description for description in descriptions)
