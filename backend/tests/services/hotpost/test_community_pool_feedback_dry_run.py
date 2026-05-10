from __future__ import annotations

from pathlib import Path

from app.services.community.interest_tag_catalog import load_interest_tag_catalog
from app.services.hotpost.community_pool_feedback_dry_run import build_pool_feedback_dry_run


SERVICE_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "hotpost"
    / "community_pool_feedback_dry_run.py"
)


def _audit_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "scope_id": "ecommerce-sellers",
        "community": "ShopifyDev",
        "topic_cluster_id": "unit-economics-and-platform-risk",
        "collected_candidates": 0,
        "draft_count": 0,
        "published_count": 0,
        "reject_count": 0,
        "duplicate_count": 0,
        "suggested_action": "keep_testing",
        "semantic_feedback": {},
    }
    row.update(overrides)
    return row


def test_no_evidence_stays_keep_testing_even_if_audit_says_promote() -> None:
    payload = build_pool_feedback_dry_run(
        {"rows": [_audit_row(suggested_action="promote_candidate")]},
        pool_community_keys=set(),
    )

    row = payload["rows"][0]

    assert row["feedback_action"] == "keep_testing"
    assert row["evidence"]["total_evidence"] == 0
    assert payload["contracts"]["writes_db"] is False
    assert payload["contracts"]["auto_promote"] is False


def test_promote_candidate_maps_user_tags_from_catalog_refs() -> None:
    source_ref = "topic_cluster:unit-economics-and-platform-risk"
    catalog = load_interest_tag_catalog()
    expected_tags = [tag.display_name for tag in catalog.tags if source_ref in tag.source_refs]
    payload = build_pool_feedback_dry_run(
        {
            "rows": [
                _audit_row(
                    collected_candidates=3,
                    draft_count=1,
                    published_count=2,
                    suggested_action="promote_candidate",
                )
            ]
        },
        pool_community_keys=set(),
        catalog=catalog,
    )

    row = payload["rows"][0]

    assert row["feedback_action"] == "promote_candidate"
    assert row["value_assessment"]["stage"] == "pool_candidate"
    assert row["suggested_user_tags"] == expected_tags
    assert row["already_in_pool"] is False


def test_single_published_probe_is_validated_but_not_pool_candidate() -> None:
    payload = build_pool_feedback_dry_run(
        {
            "rows": [
                _audit_row(
                    community="CursorAI",
                    topic_cluster_id="workflow-friction",
                    collected_candidates=2,
                    published_count=1,
                    duplicate_count=1,
                    new_topic_count=1,
                )
            ]
        },
        pool_community_keys=set(),
    )

    row = payload["rows"][0]

    assert row["feedback_action"] == "keep_testing"
    assert row["value_assessment"]["stage"] == "validated"
    assert row["value_assessment"]["score"] > 0
    assert "published_evidence" in row["value_assessment"]["positive_signals"]
    assert "duplicate_posts" in row["value_assessment"]["risks"]


def test_no_probe_evidence_stays_observe() -> None:
    payload = build_pool_feedback_dry_run(
        {"rows": [_audit_row(community="UnusedProbe")]},
        pool_community_keys=set(),
    )

    row = payload["rows"][0]

    assert row["feedback_action"] == "keep_testing"
    assert row["value_assessment"]["stage"] == "observe"
    assert row["value_assessment"]["score"] == 0


def test_existing_pool_community_is_marked_already_in_pool() -> None:
    payload = build_pool_feedback_dry_run(
        {"rows": [_audit_row(community="r/CursorAI", collected_candidates=1)]},
        pool_community_keys={"cursorai"},
    )

    assert payload["rows"][0]["feedback_action"] == "already_in_pool"
    assert payload["summary"]["already_in_pool"] == 1


def test_risk_notes_are_split_without_duplicates() -> None:
    payload = build_pool_feedback_dry_run(
        {
            "rows": [
                _audit_row(
                    collected_candidates=2,
                    duplicate_count=1,
                    noise_notes="duplicate_posts, not_published_yet",
                )
            ]
        },
        pool_community_keys=set(),
    )

    assert payload["rows"][0]["risks"] == ["duplicate_posts", "not_published_yet"]


def test_feedback_planner_does_not_hardcode_user_tag_names() -> None:
    source = SERVICE_SOURCE.read_text(encoding="utf-8")
    catalog = load_interest_tag_catalog()

    assert not any(tag.display_name in source for tag in catalog.tags)
