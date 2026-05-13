from __future__ import annotations

from datetime import date

from app.services.hotpost.community_discovery_audit import build_community_discovery_audit


def test_community_discovery_audit_is_read_only_and_keeps_probe_contracts() -> None:
    report = build_community_discovery_audit(
        experimental_by_scope={
            "ecommerce-sellers": [
                {
                    "scope_id": "ecommerce-sellers",
                    "topic_cluster_id": "edc",
                    "community": "EDC",
                }
            ]
        },
        experimental_candidates=[
            {
                "candidate_id": "cand-ecommerce-sellers-a",
                "source_scope_id": "ecommerce-sellers",
                "matched_subreddit": "EDC",
                "post_id": "post-a",
                "title": "EDC buyers compare slim pouches",
                "topic_pack_id": "selection-signals",
                "topic_cluster_id": "edc",
                "topic_cluster_ids": ["edc"],
                "named_topic_ids": ["crossborder-sku-7d-seller-validation"],
                "matched_keywords": ["better carry setup"],
                "intent_tags": ["求推荐"],
            },
            {
                "candidate_id": "cand-ecommerce-sellers-b",
                "source_scope_id": "ecommerce-sellers",
                "matched_subreddit": "EDC",
                "post_id": "post-a",
                "title": "EDC buyers compare slim pouches again",
                "topic_pack_id": "selection-signals",
                "topic_cluster_id": "edc",
                "topic_cluster_ids": ["edc"],
                "matched_keywords": ["better carry setup"],
                "intent_tags": ["替换"],
            },
        ],
        drafts=[{"draft_id": "draft-a", "candidate_id": "cand-ecommerce-sellers-a"}],
        published=[
            {
                "card_id": "card-cand-ecommerce-sellers-a-validate",
                "source_scope_id": "ecommerce-sellers",
                "top_community": "r/EDC",
                "title": "EDC 玩家开始找更薄的收纳包",
                "topic_pack_id": "selection-signals",
                "topic_cluster_id": "edc",
                "topic_cluster_ids": ["edc"],
                "intent_tags": ["求推荐"],
            }
        ],
        rejected_candidate_ids={"cand-ecommerce-sellers-b"},
        report_date=date(2026, 5, 8),
    )

    assert report["schema_version"] == "hotpost-community-discovery-audit/v1"
    assert report["contracts"] == {
        "experimental_communities_are_probe_only": True,
        "default_daily_collect_includes_experimental": False,
        "auto_promote": False,
        "writes_db": False,
        "experimental_candidate_store": "backend/data/hotpost/experimental_candidates/<scope>.json",
    }
    row = report["rows"][0]
    assert row["community"] == "edc"
    assert row["collected_candidates"] == 2
    assert row["draft_count"] == 1
    assert row["published_count"] == 1
    assert row["reject_count"] == 1
    assert row["duplicate_count"] == 1
    assert row["new_topic_count"] == 1
    assert row["suggested_action"] == "keep_testing"
    assert row["semantic_feedback"]["frequent_entities"][:2] == [
        "better carry setup",
        "crossborder-sku-7d-seller-validation",
    ]
    assert "EDC 选品" in row["semantic_feedback"]["product_tags"]
    assert row["semantic_feedback"]["sample_titles"]


def test_community_discovery_audit_keeps_empty_probe_for_testing() -> None:
    report = build_community_discovery_audit(
        experimental_by_scope={
            "ai-automation": [
                {
                    "scope_id": "ai-automation",
                    "topic_cluster_id": "workflow-friction",
                    "community": "r/unusedprobe",
                }
            ]
        },
        experimental_candidates=[],
        drafts=[],
        published=[],
        rejected_candidate_ids=set(),
        report_date=date(2026, 5, 8),
    )

    row = report["rows"][0]
    assert row["community"] == "unusedprobe"
    assert row["noise_notes"] == "no_signal_yet"
    assert row["suggested_action"] == "keep_testing"
