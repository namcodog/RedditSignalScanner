from __future__ import annotations

from app.services.hotpost.topic_metadata import merge_topic_metadata, resolve_topic_metadata


def test_resolve_topic_metadata_infers_named_topic_and_cluster_from_candidate_shape() -> None:
    item = {
        "source_scope_id": "ai-automation",
        "topic_pack_id": "upstream-winds",
        "title": "Karpathy LLM Wiki is showing up with local-first repo examples",
        "query": "karpathy llm wiki",
        "matched_subreddit": "LLM",
        "matched_keywords": ["karpathy-llm-wiki"],
        "source_communities": ["r/LLM"],
    }

    metadata = resolve_topic_metadata(item)

    assert metadata["topic_pack_id"] == "upstream-winds"
    assert metadata["topic_cluster_id"] == "key-people-and-route"
    assert "key-people-and-route" in metadata["topic_cluster_ids"]
    assert metadata["named_topic_ids"] == ["karpathy-llm-wiki"]


def test_resolve_topic_metadata_prefers_semantic_pack_for_listing_reason() -> None:
    ai_item = {
        "source_scope_id": "ai-automation",
        "topic_pack_id": "upstream-winds",
        "title": "Are AI tools actually making you too productive to switch off?",
        "primary_reason": "upstream-winds:listing_hot",
        "matched_subreddit": "OpenAI",
        "source_communities": ["r/OpenAI"],
        "evidence_quotes": [
            {"text": "I find myself wanting to make sure Claude is always working on something."},
        ],
    }
    growth_item = {
        "source_scope_id": "business-growth-ops",
        "topic_pack_id": "paid-economics",
        "title": "Booking appointments vs form submission",
        "primary_reason": "paid-economics:listing_rising",
        "matched_subreddit": "PPC",
        "source_communities": ["r/PPC"],
        "evidence_quotes": [
            {"text": "Use the booking event. Form submission is the wrong conversion signal for this funnel."},
        ],
    }

    ai_metadata = resolve_topic_metadata(ai_item)
    growth_metadata = resolve_topic_metadata(growth_item)

    assert ai_metadata["topic_pack_id"] == "tools-efficiency"
    assert ai_metadata["topic_cluster_id"] == "workflow-friction"
    assert growth_metadata["topic_pack_id"] == "funnel-conversion"
    assert growth_metadata["topic_cluster_id"] == "funnel"


def test_merge_topic_metadata_unions_clusters_and_named_topics() -> None:
    metadata = merge_topic_metadata(
        [
            {
                "source_scope_id": "ecommerce-sellers",
                "topic_pack_id": "selection-signals",
                "topic_cluster_ids": ["pet"],
                "named_topic_ids": ["pet-supplies"],
            },
            {
                "source_scope_id": "ecommerce-sellers",
                "topic_pack_id": "selection-signals",
                "topic_cluster_ids": ["outdoor"],
                "named_topic_ids": ["flashlight-selection"],
            },
        ]
    )

    assert metadata["topic_pack_id"] == "selection-signals"
    assert metadata["topic_cluster_ids"] == ["pet", "outdoor", "edc"]
    assert metadata["named_topic_ids"] == ["pet-supplies", "flashlight-selection"]


def test_resolve_topic_metadata_preserves_growth_listing_bridge_pack() -> None:
    organic_item = {
        "source_scope_id": "business-growth-ops",
        "topic_pack_id": "organic-discovery",
        "title": "11 months in and organic traffic is up but lead quality keeps getting worse",
        "primary_reason": "organic-discovery:listing_keyword_bridge",
        "matched_subreddit": "Blogging",
        "source_communities": ["r/Blogging"],
        "matched_keywords": ["organic traffic", "lead quality"],
    }
    funnel_item = {
        "source_scope_id": "business-growth-ops",
        "topic_pack_id": "funnel-conversion",
        "title": "Need a New Payment Processor",
        "primary_reason": "funnel-conversion:listing_keyword_bridge",
        "matched_subreddit": "shopify",
        "source_communities": ["r/shopify"],
        "matched_keywords": ["payment processor", "need a new"],
    }

    organic_metadata = resolve_topic_metadata(organic_item)
    funnel_metadata = resolve_topic_metadata(funnel_item)

    assert organic_metadata["topic_pack_id"] == "organic-discovery"
    assert funnel_metadata["topic_pack_id"] == "funnel-conversion"
